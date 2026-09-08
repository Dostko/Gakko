from __future__ import annotations

import queue
import threading
from datetime import date
from pathlib import Path

from PySide6.QtCore import QThread, Signal


from .Qwen_oturum.qwen_ayarlar import (
    PROJECT_ROOT,
    QWEN_MD_PATH,
    _CANCELLED,
    _STOP,
)
from .Qwen_oturum.qwen_araclari import QwenAraclariMixin
from .Qwen_oturum.qwen_dosya_ekleri import QwenDosyaEkleriMixin
from .Qwen_oturum.qwen_model import QwenModelMixin


class QwenSession(
    QwenModelMixin,
    QwenDosyaEkleriMixin,
    QwenAraclariMixin,
    QThread,
):
    ready = Signal()
    reply_ready = Signal(str)
    error_ready = Signal(str)
    cancelled = Signal()
    context_remaining = Signal(float)

    def __init__(self, active_project_root=None):
        super().__init__()

        self.active_project_root = (
            Path(active_project_root).resolve()
            if active_project_root is not None
            else None
        )

        self._ready = False
        self._stopping = False

        self._cancel_requested = threading.Event()

        self._active_process_lock = threading.Lock()
        self._active_process = None

        self._prompt_queue = queue.Queue()

        self._messages_lock = threading.Lock()
        self._messages = []

        self._system_message = {
            "role": "system",
            "content": self._load_startup_context(),
        }

    @property
    def is_ready(self):
        return self._ready

    def _load_startup_context(self):
        if not QWEN_MD_PATH.exists() or not QWEN_MD_PATH.is_file():
            raise RuntimeError(
                f"QWEN.md bulunamadı: {QWEN_MD_PATH}"
            )

        text = QWEN_MD_PATH.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()

        if not text:
            raise RuntimeError(
                f"QWEN.md boş: {QWEN_MD_PATH}"
            )

        current_date = date.today().isoformat()

        return (
            "Sen GAKKO'nun ana Qwen modelisin.\n"
            f"Güncel sistem tarihi: {current_date}\n"
            "Aşağıdaki QWEN.md yalnız başlangıç kapısıdır.\n"
            "===== QWEN.md =====\n"
            f"{text}\n"
            "===== /QWEN.md ====="
        )

    def _resolve_requested_path(self, path):
        raw = (
            str(path or "")
            .strip()
            .strip('"')
            .strip("'")
        )

        if not raw:
            raise ValueError("Boş dosya yolu.")

        candidate = Path(raw)

        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate

        return candidate.resolve()


    def submit_prompt(self, text):
        text = str(
            text or ""
        ).strip()

        if not text:
            self.error_ready.emit(
                "Boş mesaj gönderilemez."
            )
            return False

        if not self._ready:
            self.error_ready.emit(
                "Qwen henüz hazır değil."
            )
            return False

        self._cancel_requested.clear()

        self._prompt_queue.put(
            text
        )

        return True

    def reset_context(self):
        if not self._ready:
            self.error_ready.emit(
                "Qwen henüz hazır değil."
            )
            return False

        with self._messages_lock:
            self._messages.clear()

        self.context_remaining.emit(
            100.0
        )

        return True

    def _messages_for_prompt(
        self,
        text,
    ):
        with self._messages_lock:
            return [
                self._system_message,
                *self._messages,
                {
                    "role": "user",
                    "content": text,
                },
            ]

    def _remember_exchange(
        self,
        user_text,
        assistant_text,
    ):
        with self._messages_lock:
            self._messages.append(
                {
                    "role": "user",
                    "content": user_text,
                }
            )

            self._messages.append(
                {
                    "role": "assistant",
                    "content": assistant_text,
                }
            )

    def _notify_cancelled(self):
        self._cancel_requested.clear()

        print(
            "[QWEN] İşlem durduruldu.",
            flush=True,
        )

        self.cancelled.emit()

    def run(self):
        self._ready = True

        self.context_remaining.emit(
            100.0
        )

        self.ready.emit()

        try:
            while not self._stopping:
                try:
                    item = (
                        self._prompt_queue.get(
                            timeout=0.1
                        )
                    )

                except queue.Empty:
                    continue

                if item is _STOP:
                    break

                user_text = str(item)

                prepared_user_text = (
                    self._prepare_user_text(
                        user_text
                    )
                )

                try:
                    reply = (
                        self._chat_with_tools(
                            prepared_user_text
                        )
                    )

                except Exception as error:
                    if self._stopping:
                        break

                    if (
                        self._cancel_requested
                        .is_set()
                    ):
                        self._notify_cancelled()

                    else:
                        self.error_ready.emit(
                            str(error)
                        )

                    continue

                if (
                    self._stopping
                    or reply is None
                ):
                    break

                if reply is _CANCELLED:
                    self._notify_cancelled()
                    continue

                self._remember_exchange(
                    prepared_user_text,
                    reply,
                )

                self.reply_ready.emit(
                    reply
                )

        finally:
            self._ready = False

    def stop(self):
        self._stopping = True
        self._ready = False

        self.cancel_current()

        self._prompt_queue.put(
            _STOP
        )
