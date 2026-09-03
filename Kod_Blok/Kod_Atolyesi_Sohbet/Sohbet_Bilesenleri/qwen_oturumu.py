import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from Sohbet_Bilesenleri.proje_dosya_yardimcilari import PROJECT_ROOT, YUVA_ROOT


def build_qwen_args(qwen_exe, session_id, events_file, input_file, project_root=None):
    args = [
        str(qwen_exe),
        "--session-id",
        str(session_id),
        "--include-directories",
        str(YUVA_ROOT),
    ]

    if project_root is not None:
        args.extend(["--include-directories", str(project_root)])

    args.extend([
        "--approval-mode",
        "auto",
        "--json-file",
        str(events_file),
        "--input-file",
        str(input_file),
    ])

    return args

class QwenSession(QThread):
    ready = Signal()
    reply_ready = Signal(str)
    error_ready = Signal(str)

    def __init__(self, active_project_root=None):
        super().__init__()
        self.session_id = str(uuid.uuid4())
        self.active_project_root = (
            Path(active_project_root)
            if active_project_root is not None
            else None
        )
        self.process = None
        self._stopping = False
        self._ready = False
        self._input_lock = threading.Lock()
        self._last_assistant_text = ""
        self._pty_output_tail = ""

        self.runtime_dir = Path(tempfile.mkdtemp(prefix="gakko-qwen-"))
        self.events_file = self.runtime_dir / "events.jsonl"
        self.input_file = self.runtime_dir / "input.jsonl"
        self.events_file.write_text("", encoding="utf-8")
        self.input_file.write_text("", encoding="utf-8")

    @property
    def is_ready(self):
        return self._ready

    def _find_qwen(self):
        qwen_exe = shutil.which("qwen") or shutil.which("qwen.cmd")
        if not qwen_exe:
            raise RuntimeError("Qwen Code bulunamadı.")
        return qwen_exe

    def _start_qwen(self):
        if sys.platform != "win32":
            raise RuntimeError("Bu Gakko terminal köprüsü Windows için hazırlanmıştır.")

        try:
            from winpty import PtyProcess
        except ImportError as error:
            raise RuntimeError(
                "Kalıcı Qwen terminal köprüsü için pywinpty bulunamadı."
            ) from error

        qwen_exe = self._find_qwen()
        qwen_args = build_qwen_args(
            qwen_exe,
            self.session_id,
            self.events_file,
            self.input_file,
            self.active_project_root,
        )

        if qwen_exe.lower().endswith((".cmd", ".bat")):
            inner = subprocess.list2cmdline(qwen_args)
            command = [
                os.environ.get("COMSPEC", "cmd.exe"),
                "/d",
                "/s",
                "/c",
                inner,
            ]
        else:
            command = qwen_args

        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")

        self.process = PtyProcess.spawn(
            command,
            cwd=str(PROJECT_ROOT),
            env=env,
            dimensions=(40, 120),
        )

        threading.Thread(
            target=self._drain_pty_output,
            name="gakko-qwen-pty-drain",
            daemon=True,
        ).start()

    def _drain_pty_output(self):
        process = self.process
        if process is None:
            return

        while not self._stopping:
            try:
                chunk = process.read(4096)
            except EOFError:
                break
            except Exception:
                if not self._stopping:
                    time.sleep(0.05)
                continue

            if not chunk:
                try:
                    if not process.isalive():
                        break
                except Exception:
                    break
                time.sleep(0.05)
                continue

            self._pty_output_tail = (self._pty_output_tail + str(chunk))[-4000:]

    def submit_prompt(self, text):
        text = str(text or "").strip()
        if not text:
            self.error_ready.emit("Boş mesaj gönderilemez.")
            return False

        if not self._ready:
            self.error_ready.emit("Qwen Code henüz hazır değil.")
            return False

        command = {
            "type": "submit",
            "text": text,
        }
        line = json.dumps(command, ensure_ascii=False) + "\n"

        try:
            with self._input_lock:
                with self.input_file.open("a", encoding="utf-8", newline="") as handle:
                    handle.write(line)
                    handle.flush()
            return True
        except Exception as error:
            self.error_ready.emit(f"Qwen Code mesajı gönderilemedi: {error}")
            return False

    def _extract_assistant_text(self, event):
        if not isinstance(event, dict) or event.get("type") != "assistant":
            return ""

        message = event.get("message") or {}
        content = message.get("content") or []
        parts = []

        for item in content:
            if (
                isinstance(item, dict)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
            ):
                text = item["text"].strip()
                if text:
                    parts.append(text)

        return "\n".join(parts).strip()

    def _handle_event(self, event):
        if not isinstance(event, dict):
            return

        if event.get("type") == "system" and event.get("subtype") == "session_start":
            if not self._ready:
                self._ready = True
                self.ready.emit()
            return

        assistant_text = self._extract_assistant_text(event)
        if assistant_text:
            self._last_assistant_text = assistant_text
            return

        if event.get("type") == "stream_event":
            stream_event = event.get("event") or {}

            if stream_event.get("type") == "message_stop":
                reply = self._last_assistant_text.strip()
                self._last_assistant_text = ""

                if reply:
                    self.reply_ready.emit(reply)
                else:
                    return

    def _tail_events(self):
        position = 0
        pending = ""

        while not self._stopping:
            try:
                if not self.events_file.exists():
                    time.sleep(0.05)
                    continue

                with self.events_file.open("r", encoding="utf-8", errors="replace") as handle:
                    handle.seek(position)
                    chunk = handle.read()
                    position = handle.tell()

                if chunk:
                    pending += chunk
                    lines = pending.split("\n")
                    pending = lines.pop()

                    for raw_line in lines:
                        raw_line = raw_line.strip()
                        if not raw_line:
                            continue
                        try:
                            event = json.loads(raw_line)
                        except json.JSONDecodeError:
                            continue
                        self._handle_event(event)

                process = self.process
                if process is not None:
                    try:
                        alive = process.isalive()
                    except Exception:
                        alive = False

                    if not alive:
                        if not self._stopping:
                            detail = self._pty_output_tail.strip()
                            self.error_ready.emit(
                                "Qwen Code terminal oturumu kapandı."
                                + (f"\n{detail[-1200:]}" if detail else "")
                            )
                        break

                time.sleep(0.05)

            except Exception as error:
                if not self._stopping:
                    self.error_ready.emit(f"Qwen Code olay akışı okunamadı: {error}")
                time.sleep(0.1)

    def run(self):
        try:
            self._start_qwen()
            self._tail_events()
        except Exception as error:
            if not self._stopping:
                self.error_ready.emit(str(error))
        finally:
            self._terminate_process()
            self._cleanup_runtime_files()

    def stop(self):
        self._stopping = True
        self._ready = False
        self._terminate_process()

    def _terminate_process(self):
        process = self.process
        self.process = None

        if process is None:
            return

        try:
            if process.isalive():
                process.terminate(force=True)
        except Exception:
            try:
                process.close(force=True)
            except Exception:
                pass

    def _cleanup_runtime_files(self):
        try:
            for path in (self.events_file, self.input_file):
                if path.exists():
                    path.unlink()
            if self.runtime_dir.exists():
                self.runtime_dir.rmdir()
        except Exception:
            pass
