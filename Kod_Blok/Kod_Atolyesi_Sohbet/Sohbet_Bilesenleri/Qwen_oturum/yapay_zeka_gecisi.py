from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from .qwen_ayarlar import (
    STRATA_HEALTH_URL,
    STRATA_HOST,
    STRATA_MODELS,
    _CANCELLED,
)


_STRATA_PORT = "8080"
_MIN_FREE_RAM_BYTES = 36 * 1024**3
_RUNTIME_WAIT_SECONDS = 180.0


def _read_json(url, timeout=2.0):
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _normalize_identity(value):
    return (
        str(value or "")
        .casefold()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _strata_runtime_info():
    try:
        health = _read_json(STRATA_HEALTH_URL)
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return {
            "loaded": False,
            "status": "offline",
            "max_context": 0,
            "identity": "",
        }

    loaded = bool(health.get("loaded"))
    status = str(health.get("status") or "").strip().casefold()
    identity_parts = [health.get("model")]

    if loaded and status == "ok":
        try:
            props = _read_json(f"{STRATA_HOST}/props")
        except (OSError, URLError, ValueError, json.JSONDecodeError):
            props = {}

        identity_parts.extend(
            (
                props.get("model"),
                props.get("model_id"),
                props.get("model_path"),
            )
        )

    identity = " | ".join(
        str(item).strip()
        for item in identity_parts
        if str(item or "").strip()
    )

    try:
        max_context = int(health.get("max_context") or 0)
    except (TypeError, ValueError):
        max_context = 0

    return {
        "loaded": loaded,
        "status": status,
        "max_context": max_context,
        "identity": identity,
    }


def _runtime_matches_model(info, config):
    identity = _normalize_identity(info.get("identity"))
    expected = _normalize_identity(config.get("model"))
    return bool(identity and expected and expected in identity)


def _context_cli_value(context_size):
    size = int(context_size)
    if size % 1024 == 0:
        return f"{size // 1024}k"
    return str(size)


def _strata_command_path():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidate = (
            Path(local_app_data)
            / "Strata"
            / "terminal"
            / "current"
            / "bin"
            / "strata.cmd"
        )
        if candidate.is_file():
            return candidate

    fallback = shutil.which("strata") or shutil.which("strata.cmd")
    if fallback:
        return Path(fallback)

    raise RuntimeError(
        "Strata Terminal bulunamadı. GAKKO_R1, Strata Terminal kurulumunu "
        "kullanarak modeli servis eder."
    )


def _run_strata_cli(*args, timeout=600.0):
    strata_path = _strata_command_path()

    if os.name == "nt" and strata_path.suffix.casefold() in {".cmd", ".bat"}:
        comspec = os.environ.get("COMSPEC") or "cmd.exe"
        command = [comspec, "/d", "/c", str(strata_path), *map(str, args)]
    else:
        command = [str(strata_path), *map(str, args)]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=(
            subprocess.CREATE_NO_WINDOW
            if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW")
            else 0
        ),
    )

    return {
        "returncode": int(completed.returncode),
        "stdout": str(completed.stdout or "").strip(),
        "stderr": str(completed.stderr or "").strip(),
    }


def _available_ram_bytes():
    if os.name != "nt":
        return None

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None

    return int(status.ullAvailPhys)


def _ensure_launch_memory():
    available = _available_ram_bytes()

    if available is None or available >= _MIN_FREE_RAM_BYTES:
        return

    available_gib = available / 1024**3

    raise RuntimeError(
        "Strata modeli başlatılmadı: yalnızca "
        f"{available_gib:.1f} GiB boş fiziksel RAM var. "
        "Bu koruma, başka bir büyük Strata modeli veya ağır program açıkken "
        "ikinci modeli yükleyip Windows'u kilitlememek için devreye girdi."
    )


def _wait_for_runtime(
    expected_loaded,
    config=None,
    timeout=_RUNTIME_WAIT_SECONDS,
):
    deadline = time.monotonic() + float(timeout)
    last_info = None

    while time.monotonic() < deadline:
        last_info = _strata_runtime_info()

        is_loaded = (
            bool(last_info.get("loaded"))
            and last_info.get("status") == "ok"
        )

        if expected_loaded:
            if (
                is_loaded
                and (
                    config is None
                    or _runtime_matches_model(last_info, config)
                )
            ):
                return last_info

        elif not is_loaded:
            return last_info

        time.sleep(0.5)

    if expected_loaded:
        expected = config.get("model") if config else "model"

        raise RuntimeError(
            f"Strata {expected} modelini "
            f"{_RUNTIME_WAIT_SECONDS:.0f} saniye içinde hazır edemedi."
        )

    raise RuntimeError(
        "Strata önceki modeli süre içinde tamamen durduramadı; "
        "yeni model güvenlik için başlatılmadı."
    )


def _stop_strata_runtime():
    result = _run_strata_cli(
        "launch",
        "--stop",
        "--output",
        "json",
        timeout=120.0,
    )

    if result["returncode"] not in {0}:
        detail = (
            result["stderr"]
            or result["stdout"]
            or "bilinmeyen hata"
        )

        raise RuntimeError(
            f"Strata modeli durdurulamadı: {detail}"
        )

    return _wait_for_runtime(False, timeout=90.0)


def _launch_strata_runtime(config):
    _ensure_launch_memory()

    result = _run_strata_cli(
        "launch",
        "--model",
        config["model"],
        "--family",
        config["family"],
        "--context",
        _context_cli_value(config["context"]),
        "--tune",
        "skip",
        "--access",
        "local",
        "--port",
        _STRATA_PORT,
        "--yes",
        "--no-tui",
        "--output",
        "json",
        timeout=600.0,
    )

    if result["returncode"] != 0:
        detail = (
            result["stderr"]
            or result["stdout"]
            or "bilinmeyen hata"
        )

        raise RuntimeError(
            f"Strata modeli başlatılamadı: {detail}"
        )

    try:
        payload = json.loads(result["stdout"] or "{}")
    except json.JSONDecodeError:
        payload = {}

    if isinstance(payload, dict) and payload.get("serving") is False:
        detail = (
            payload.get("engine_problem")
            or payload.get("error")
            or result["stdout"]
        )

        raise RuntimeError(
            f"Strata modeli servis edemedi: {detail}"
        )

    return _wait_for_runtime(True, config=config)


def modeli_hazirla(session, model):
    model_name = str(model or "").strip()
    config = STRATA_MODELS.get(model_name)

    if config is None:
        raise ValueError(
            f"Bilinmeyen GAKKO model rolü: {model_name}"
        )

    if session._stopping or session._cancel_requested.is_set():
        return _CANCELLED

    info = _strata_runtime_info()

    is_loaded = (
        bool(info.get("loaded"))
        and info.get("status") == "ok"
    )

    if is_loaded and _runtime_matches_model(info, config):
        max_context = int(info.get("max_context") or 0)
        required_context = int(config["context"])

        if max_context and max_context < required_context:
            _stop_strata_runtime()
            session._strata_model_role = None

        else:
            session._strata_model_role = model_name
            session._active_context_size = (
                max_context or required_context
            )
            return True

    elif is_loaded:
        _stop_strata_runtime()
        session._strata_model_role = None

    info = _launch_strata_runtime(config)

    required_context = int(config["context"])
    max_context = int(info.get("max_context") or 0)

    session._strata_model_role = model_name
    session._active_context_size = max_context or required_context
    session._strata_owned = True

    return True


def strata_motorunu_durdur(session):
    if not bool(
        getattr(session, "_strata_owned", False)
    ):
        return True

    try:
        _stop_strata_runtime()

    finally:
        session._strata_owned = False
        session._strata_model_role = None

    return True


def uzman_model_cagir(session, model, **chat_arguments):
    ready = modeli_hazirla(session, model)

    if ready is _CANCELLED:
        return _CANCELLED

    return session._chat(**chat_arguments)