from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path

from mcp import StdioServerParameters

GIT_PUSH_TOOL_NAME = "git_push"
GIT_COMMIT_VERIFIED_MARKER = "[GIT COMMIT DOĞRULANDI]"
GIT_PUSH_TOOL = {
    "type": "function",
    "function": {
        "name": GIT_PUSH_TOOL_NAME,
        "description": (
            "Aktif master branch'ini origin/master uzak dalına gönderir. "
            "Yalnız kullanıcı açıkça onay verdikten sonra kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}
GIT_COMMIT_SUCCESS_PATTERNS = (
    r"\bcommit\b.{0,80}\b(başarıyla|başarılı|tamamlandı|gerçekleştirildi|oluşturuldu)",
    r"\bgit kayd[ıi]\b.{0,80}\b(alındı|başarıyla|başarılı|tamamlandı|oluşturuldu)",
    r"\bcommit\b.{0,80}\b(successfully|successful|completed|created)",
)
GIT_APPROVAL_ACTIONS = {"git_add", "git_commit", GIT_PUSH_TOOL_NAME}
GIT_APPROVAL_RESPONSES = {
    "evet", "evet kanka", "onay", "onaylıyorum", "onayliyorum",
    "tamam", "tamam kanka", "yap", "devam", "devam et",
}
GIT_CANCEL_RESPONSES = {"hayır", "hayir", "iptal", "vazgeç", "vazgec"}


def _approval_arguments(arguments):
    return {
        key: value for key, value in dict(arguments or {}).items()
        if key != "repo_path"
    }


def begin_git_approval_turn(owner, user_text):
    owner._git_approved_action = None
    pending = getattr(owner, "_git_pending_approval", None)
    if not pending:
        return

    response = str(user_text or "").strip().casefold()
    response = re.sub(r"[.!?]+$", "", response).strip()
    if response in GIT_CANCEL_RESPONSES:
        owner._git_pending_approval = None
        return
    if response in GIT_APPROVAL_RESPONSES:
        owner._git_approved_action = pending["action"]
        if pending.get("arguments") is not None:
            return {
                "action": pending["action"],
                "arguments": dict(pending["arguments"]),
            }


async def execute_approved_git_action(owner, runtime, user_text):
    request = begin_git_approval_turn(owner, user_text)
    if request is None:
        return None, False
    result = await call_git_tool(
        owner, runtime, request["action"], request["arguments"]
    )
    verified = (
        request["action"] == "git_commit"
        and GIT_COMMIT_VERIFIED_MARKER in str(result)
    )
    return result, verified


def _git_approval_message(action, arguments=None):
    labels = {
        "git_add": "GIT ADD",
        "git_commit": "GIT COMMIT",
        GIT_PUSH_TOOL_NAME: "GIT PUSH",
    }
    detail = ""
    if action == "git_add":
        paths = (arguments or {}).get("files") or ()
        if paths:
            detail = "\nStage edilecek yollar:\n" + "\n".join(
                f"- {path}" for path in paths
            )
    return (
        f"[{labels[action]} ONAYI GEREKLİ]{detail}\n"
        "Bu işlem çalıştırılmadı. Kullanıcıdan açık onay iste ve "
        "bu cevabı bitir; aynı turda başka Git değişikliği yapma."
    )


def _require_git_approval(owner, action, arguments):
    current_arguments = _approval_arguments(arguments)
    pending = getattr(owner, "_git_pending_approval", None)
    approved_action = getattr(owner, "_git_approved_action", None)

    if pending and pending.get("action") != action:
        return _git_approval_message(
            pending["action"],
            pending.get("arguments"),
        )
    if pending and approved_action == action:
        expected_arguments = pending.get("arguments")
        if expected_arguments is None or expected_arguments == current_arguments:
            return None

    owner._git_pending_approval = {
        "action": action,
        "arguments": current_arguments,
    }
    return _git_approval_message(action, arguments)


def _complete_git_action(owner, action):
    owner._git_approved_action = None
    next_action = {
        "git_add": "git_commit",
        "git_commit": GIT_PUSH_TOOL_NAME,
    }.get(action)
    owner._git_pending_approval = (
        {
            "action": next_action,
            "arguments": {} if next_action == GIT_PUSH_TOOL_NAME else None,
        }
        if next_action else None
    )


def _git_result_failed(result):
    return str(result or "").strip().startswith(
        ("[MCP HATA]", "[GIT HATA]", "[TOOL HATA]")
    )


def guard_git_commit_claim(text, git_commit_verified):
    final_text = str(text or "").strip()

    if git_commit_verified:
        return final_text

    normalized = final_text.casefold()
    claims_success = any(
        re.search(pattern, normalized, flags=re.DOTALL)
        for pattern in GIT_COMMIT_SUCCESS_PATTERNS
    )

    if not claims_success:
        return final_text

    return (
        "[GIT HATA] Git commit bu turda Git aracıyla "
        "doğrulanmadı. Başarı bildirimi engellendi."
    )


def _git_runner():
    uvx_path = shutil.which("uvx")
    if uvx_path:
        return uvx_path, ["mcp-server-git"]

    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path, ["tool", "run", "mcp-server-git"]

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        packages_root = (
            Path(local_appdata)
            / "Microsoft"
            / "WinGet"
            / "Packages"
        )
        candidates = sorted(
            packages_root.glob(
                "astral-sh.uv_Microsoft.Winget.Source_*/uv.exe"
            )
        )
        if candidates:
            return str(candidates[0]), [
                "tool",
                "run",
                "mcp-server-git",
            ]

    raise RuntimeError(
        "Git MCP başlatılamadı: uv/uvx bulunamadı."
    )


def create_git_server_parameters(project_root, environment):
    command, args = _git_runner()
    return StdioServerParameters(
        command=command,
        args=[
            *args,
            "--repository",
            str(Path(project_root).resolve()),
        ],
        env=environment,
    )


def resolve_git_repository(project_root, runner=subprocess.run):
    project_path = str(Path(project_root).resolve())
    result = runner(
        [
            "git",
            "-C",
            project_path,
            "rev-parse",
            "--show-toplevel",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        return None

    repository_root = result.stdout.strip()
    if not repository_root:
        return None

    return Path(repository_root).resolve()


def initialize_git_repository(project_root, runner=subprocess.run):
    project_path = Path(project_root).resolve()
    result = runner(
        [
            "git",
            "-C",
            str(project_path),
            "init",
            "-b",
            "master",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"Git repository oluşturulamadı: {detail}"
        )

    return project_path


async def load_git_tools(git_client, tool_schema):
    response = await git_client.list_tools()
    remote_tools = list(
        getattr(response, "tools", response) or ()
    )

    if not remote_tools:
        raise RuntimeError("Git MCP hiçbir araç sunmadı.")

    tools = [tool_schema(tool) for tool in remote_tools]
    names = frozenset(str(tool.name) for tool in remote_tools)

    if GIT_PUSH_TOOL_NAME not in names:
        tools.append(GIT_PUSH_TOOL)
        names = names | {GIT_PUSH_TOOL_NAME}

    return remote_tools, tools, names


def _prepare_git_arguments(arguments, project_root):
    prepared = dict(arguments)
    prepared["repo_path"] = str(Path(project_root).resolve())
    return prepared


def _read_head_commit(repo_path, runner=subprocess.run):
    result = runner(
        [
            "git",
            "-C",
            str(Path(repo_path).resolve()),
            "rev-parse",
            "HEAD",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        return None

    commit_id = result.stdout.strip()
    return commit_id or None


def push_active_master(repo_path, runner=subprocess.run):
    repo = str(Path(repo_path).resolve())
    run_options = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "check": False,
    }

    branch_result = runner(
        ["git", "-C", repo, "branch", "--show-current"],
        **run_options,
    )
    if branch_result.returncode != 0:
        detail = (branch_result.stderr or branch_result.stdout).strip()
        return f"[GIT HATA] Aktif branch okunamadı: {detail}"

    branch = branch_result.stdout.strip()
    if branch != "master":
        return (
            "[GIT HATA] Push durduruldu: aktif branch "
            f"'{branch or 'bilinmiyor'}'; beklenen branch 'master'."
        )

    push_result = runner(
        ["git", "-C", repo, "push", "origin", "master"],
        **run_options,
    )
    detail = (push_result.stdout or push_result.stderr).strip()
    if push_result.returncode != 0:
        return f"[GIT HATA] Git push başarısız: {detail}"

    return f"[GIT PUSH BAŞARILI] origin/master\n{detail}".rstrip()


async def call_git_tool(
    owner,
    runtime,
    name,
    arguments,
    runner=subprocess.run,
):
    arguments = _prepare_git_arguments(
        arguments,
        runtime.git_repo_root,
    )

    if name in GIT_APPROVAL_ACTIONS:
        approval_message = _require_git_approval(
            owner,
            name,
            arguments,
        )
        if approval_message is not None:
            return approval_message

    if name == GIT_PUSH_TOOL_NAME:
        result = await asyncio.to_thread(
            push_active_master,
            arguments["repo_path"],
            runner,
        )
        if not _git_result_failed(result):
            _complete_git_action(owner, name)
        return result

    commit_before = None
    if name == "git_commit":
        commit_before = await asyncio.to_thread(
            _read_head_commit,
            arguments["repo_path"],
            runner,
        )

    result = await owner._call_mcp_tool(
        runtime.git_client,
        name,
        arguments,
    )

    if name == "git_commit":
        result_text = str(result or "").strip()
        if result_text.startswith(("[MCP HATA]", "[GIT HATA]")):
            return (
                "[GIT HATA] Git commit aracı hata döndürdü; "
                "push onayı istenmedi.\n"
                f"{result_text}"
            )

        commit_after = await asyncio.to_thread(
            _read_head_commit,
            arguments["repo_path"],
            runner,
        )

        if commit_after is None or commit_after == commit_before:
            return (
                "[GIT HATA] Git commit doğrulanamadı; "
                "deponun HEAD kimliği değişmedi. Push onayı istenmedi."
            )

        _complete_git_action(owner, name)
        result_prefix = f"{result_text}\n\n" if result_text else ""
        return (
            f"{result_prefix}"
            f"{GIT_COMMIT_VERIFIED_MARKER} {commit_after}\n\n"
            "[GIT AKIŞI] Commit başarılıysa cevabı bitirme. "
            "Kullanıcıya tam olarak 'Git push yapmamı "
            "onaylıyor musunuz?' diye sor. Kullanıcı açıkça "
            "onay vermeden git_push aracını kullanma."
        )

    if name == "git_add" and not _git_result_failed(result):
        _complete_git_action(owner, name)
        return (
            f"{result}\n\n"
            "[GIT AKIŞI] Stage işlemi tamamlandı. Commit işlemini "
            "çalıştırmadan önce kullanıcıdan ayrıca onay iste."
        )

    return result
