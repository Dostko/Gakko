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

from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView


PROJECT_ROOT = Path(r"D:\Gakko")
YUVA_ROOT = PROJECT_ROOT / "GAKKO_YUVA"
CALISMA_YONTEMLERI_ROOT = YUVA_ROOT / "Calisma_Yontemleri"
MEVCUT_PROJE_YONTEMI = CALISMA_YONTEMLERI_ROOT / "mevcut_projeyi_baslat_incele.md"
YENI_PROJE_YONTEMI = CALISMA_YONTEMLERI_ROOT / "yeni_proje_olustur.md"


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


def list_project_directory(project_root, relative_path=""):
    root = Path(project_root).resolve()
    relative = str(relative_path or "").replace("\\", "/").strip("/")
    target = root.joinpath(*([part for part in relative.split("/") if part] or [])).resolve()

    if target != root and not target.is_relative_to(root):
        raise ValueError("Proje kökü dışındaki klasörler listelenemez.")

    if not target.exists() or not target.is_dir():
        raise ValueError("İstenen proje klasörü bulunamadı.")

    entries = []
    for entry in target.iterdir():
        try:
            is_directory = entry.is_dir()
        except OSError:
            continue

        entry_relative = entry.relative_to(root).as_posix()
        entries.append({
            "name": entry.name,
            "type": "directory" if is_directory else "file",
            "path": entry_relative,
        })

    entries.sort(key=lambda item: (item["type"] != "directory", item["name"].casefold()))

    return {
        "path": relative,
        "entries": entries,
    }


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


class ChatBridge(QObject):
    reply_ready = Signal(str)
    error_ready = Signal(str)
    connection_ready = Signal()
    project_selected = Signal(str)
    project_directory_ready = Signal(str)

    def __init__(self):
        super().__init__()
        self.session = QwenSession()
        self._busy = False
        self._pending_message = None
        self.active_project_root = None

        self._bind_session(self.session)

    def _bind_session(self, session):
        session.ready.connect(self._on_ready)
        session.reply_ready.connect(self._on_reply)
        session.error_ready.connect(self._on_error)

    def start(self):
        if not self.session.isRunning():
            self.session.start()

    def _on_ready(self):
        self.connection_ready.emit()

        if self._pending_message:
            pending = self._pending_message
            self._pending_message = None
            self._busy = True
            if not self.session.submit_prompt(pending):
                self._busy = False

    def _build_project_start_prompt(self, selected_root, method_path):
        return (
            f"Aktif proje kökü: {selected_root}\n"
            f"{method_path} dosyasını oku ve bu çalışma yöntemine göre devam et. "
            "Seçilen proje kökünü aktif çalışma projesi olarak kullan. "
            "Çalışma yönteminin sınırlarını aşma."
        )

    def _restart_session_for_project(self, selected_root, startup_prompt):
        old_session = self.session
        old_session.stop()
        old_session.wait(3000)

        if old_session.isRunning():
            self.error_ready.emit("Mevcut Qwen Code oturumu kapatılamadı.")
            return False

        self.session = QwenSession(selected_root)
        self._bind_session(self.session)
        self._pending_message = startup_prompt
        self._busy = False
        return True

    def _activate_project(self, selected_root, method_path):
        selected_root = Path(selected_root)
        method_path = Path(method_path)

        if not selected_root.exists() or not selected_root.is_dir():
            self.error_ready.emit("Seçilen proje klasörü geçerli değil.")
            return False

        if not method_path.exists() or not method_path.is_file():
            self.error_ready.emit(
                f"Proje çalışma yöntemi bulunamadı: {method_path}"
            )
            return False

        startup_prompt = self._build_project_start_prompt(
            selected_root,
            method_path,
        )

        if not self._restart_session_for_project(selected_root, startup_prompt):
            return False

        self.active_project_root = selected_root
        self.project_selected.emit(str(selected_root))
        self.session.start()
        return True

    def _project_change_allowed(self):
        if self._busy:
            self.error_ready.emit(
                "Qwen Code şu anda başka bir mesaja cevap veriyor."
            )
            return False
        return True

    @Slot()
    def select_project_folder(self):
        if not self._project_change_allowed():
            return

        selected_path = QFileDialog.getExistingDirectory(
            QApplication.activeWindow(),
            "Proje Aç",
            str(PROJECT_ROOT),
        )

        selected_path = str(selected_path or "").strip()
        if not selected_path:
            return

        self._activate_project(
            Path(selected_path),
            MEVCUT_PROJE_YONTEMI,
        )

    @Slot()
    def start_new_project(self):
        if not self._project_change_allowed():
            return

        selected_path = QFileDialog.getExistingDirectory(
            QApplication.activeWindow(),
            "Yeni Proje Başlat - boş klasör seç veya oluştur",
            str(PROJECT_ROOT.parent),
        )

        selected_path = str(selected_path or "").strip()
        if not selected_path:
            return

        selected_root = Path(selected_path)
        if not selected_root.exists() or not selected_root.is_dir():
            self.error_ready.emit("Seçilen proje klasörü geçerli değil.")
            return

        try:
            if any(selected_root.iterdir()):
                self.error_ready.emit(
                    "Yeni proje için boş bir klasör seç veya oluştur. "
                    "Mevcut bir proje için Proje Aç seçeneğini kullan."
                )
                return
        except OSError as error:
            self.error_ready.emit(f"Proje klasörü okunamadı: {error}")
            return

        self._activate_project(
            selected_root,
            YENI_PROJE_YONTEMI,
        )

    @Slot(str)
    def list_project_directory(self, relative_path):
        if self.active_project_root is None:
            return

        try:
            payload = list_project_directory(
                self.active_project_root,
                relative_path,
            )
        except (OSError, ValueError) as error:
            self.error_ready.emit(f"Proje dosyaları okunamadı: {error}")
            return

        self.project_directory_ready.emit(
            json.dumps(payload, ensure_ascii=False)
        )

    @Slot(str)
    def send_message(self, message):
        message = str(message or "").strip()
        if not message:
            self.error_ready.emit("Boş mesaj gönderilemez.")
            return

        if self._busy:
            self.error_ready.emit("Qwen Code şu anda başka bir mesaja cevap veriyor.")
            return

        if not self.session.is_ready:
            self._pending_message = message
            return

        self._busy = True
        if not self.session.submit_prompt(message):
            self._busy = False

    def _on_reply(self, text):
        self._busy = False
        self.reply_ready.emit(text)

    def _on_error(self, text):
        self._busy = False
        self.error_ready.emit(text)

    def close(self):
        self.session.stop()
        self.session.wait(3000)


class GakkoSohbetPenceresi(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Gakko")
        self.resize(1200, 820)
        self.setMinimumSize(900, 620)

        self.web = QWebEngineView(self)
        self.web.setStyleSheet("background:#080b11; border:0;")
        self.web.page().setBackgroundColor(QColor("#080b11"))

        self.bridge = ChatBridge()

        self.channel = QWebChannel(self.web.page())
        self.channel.registerObject("gakkoBridge", self.bridge)
        self.web.page().setWebChannel(self.channel)

        index_path = Path(__file__).resolve().parent / "index.html"
        self.web.setUrl(QUrl.fromLocalFile(str(index_path)))

        self.setCentralWidget(self.web)
        self.bridge.start()

    def closeEvent(self, event):
        self.bridge.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gakko")

    window = GakkoSohbetPenceresi()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
