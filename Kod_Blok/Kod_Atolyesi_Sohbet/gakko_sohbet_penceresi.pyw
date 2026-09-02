import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView


PROJECT_ROOT = Path(r"D:\Gakko")
YUVA_ROOT = PROJECT_ROOT / "GAKKO_YUVA"
CALISMA_YONTEMLERI_ROOT = YUVA_ROOT / "Calisma_Yontemleri"
MEVCUT_PROJE_YONTEMI = CALISMA_YONTEMLERI_ROOT / "mevcut_projeyi_baslat_incele.md"
YENI_PROJE_YONTEMI = CALISMA_YONTEMLERI_ROOT / "yeni_proje_olustur.md"


HISTORY_RETENTION_DAYS = 30


def get_history_db_path():
    local_app_data = str(os.environ.get("LOCALAPPDATA") or "").strip()
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / ".local" / "share"

    history_dir = base / "Gakko"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / "history.sqlite3"


class ChatHistoryStore:
    def __init__(self, db_path, retention_days=HISTORY_RETENTION_DAYS):
        self.db_path = Path(db_path)
        self.retention_days = max(1, int(retention_days))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self.cleanup_expired()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT 'Yeni sohbet',
                    project_path TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_history_updated_at
                    ON conversations(updated_at);

                CREATE INDEX IF NOT EXISTS idx_history_messages_conversation
                    ON messages(conversation_id, id);
                """
            )

    @staticmethod
    def _now_iso():
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _project_name(project_path):
        clean = str(project_path or "").strip().rstrip("\\/")
        if not clean:
            return ""
        return clean.replace("\\", "/").rsplit("/", 1)[-1]

    @staticmethod
    def _title_from_message(message):
        clean = " ".join(str(message or "").split())
        if not clean:
            return "Yeni sohbet"
        if len(clean) <= 72:
            return clean
        return clean[:69].rstrip() + "..."

    def create_session(self, project_path=""):
        session_id = str(uuid.uuid4())
        now = self._now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (
                    id, created_at, updated_at, title, project_path
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, now, now, "Yeni sohbet", str(project_path or "")),
            )
        return session_id

    def add_message(self, session_id, role, content):
        session_id = str(session_id or "").strip()
        role = str(role or "").strip().lower()
        content = str(content or "").strip()

        if not session_id or role not in {"user", "assistant"} or not content:
            return False

        now = self._now_iso()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT title FROM conversations WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return False

            connection.execute(
                """
                INSERT INTO messages (
                    conversation_id, role, content, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, now),
            )

            title = row["title"]
            if role == "user" and title == "Yeni sohbet":
                title = self._title_from_message(content)

            connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?, title = ?
                WHERE id = ?
                """,
                (now, title, session_id),
            )
        return True

    def cleanup_expired(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE updated_at < ?",
                (cutoff.isoformat(timespec="seconds"),),
            )
            return max(0, int(cursor.rowcount or 0))

    def list_sessions(self, query=""):
        self.cleanup_expired()
        query = str(query or "").strip()
        params = []
        where = ""

        if query:
            needle = f"%{query}%"
            where = """
                WHERE c.title LIKE ? COLLATE NOCASE
                   OR c.project_path LIKE ? COLLATE NOCASE
                   OR EXISTS (
                       SELECT 1
                       FROM messages sm
                       WHERE sm.conversation_id = c.id
                         AND sm.content LIKE ? COLLATE NOCASE
                   )
            """
            params.extend([needle, needle, needle])

        sql = f"""
            SELECT
                c.id,
                c.created_at,
                c.updated_at,
                c.title,
                c.project_path,
                COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            {where}
            GROUP BY c.id
            HAVING COUNT(m.id) > 0
            ORDER BY c.updated_at DESC
        """

        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        return [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "title": row["title"],
                "project_path": row["project_path"],
                "project_name": self._project_name(row["project_path"]),
                "message_count": int(row["message_count"] or 0),
            }
            for row in rows
        ]

    def get_session(self, session_id):
        session_id = str(session_id or "").strip()
        if not session_id:
            return None

        with self._connect() as connection:
            conversation = connection.execute(
                """
                SELECT id, created_at, updated_at, title, project_path
                FROM conversations
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()

            if conversation is None:
                return None

            messages = connection.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()

        return {
            "id": conversation["id"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
            "title": conversation["title"],
            "project_path": conversation["project_path"],
            "project_name": self._project_name(conversation["project_path"]),
            "messages": [
                {
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                }
                for row in messages
            ],
        }

    def delete_session(self, session_id):
        session_id = str(session_id or "").strip()
        if not session_id:
            return False

        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (session_id,),
            )
            return int(cursor.rowcount or 0) > 0

    def delete_before(self, cutoff_iso):
        cutoff_text = str(cutoff_iso or "").strip()
        if not cutoff_text:
            return 0

        try:
            cutoff = datetime.fromisoformat(cutoff_text.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("Geçerli bir tarih seçilmedi.") from error

        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        cutoff = cutoff.astimezone(timezone.utc)

        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE updated_at < ?",
                (cutoff.isoformat(timespec="seconds"),),
            )
            return max(0, int(cursor.rowcount or 0))


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
    history_sessions_ready = Signal(str)
    history_session_ready = Signal(str)
    history_action_ready = Signal(str)

    def __init__(self):
        super().__init__()
        self.settings = QSettings("Gakko", "Gakko")
        self.active_project_root = self._load_last_active_project()
        self.history = ChatHistoryStore(
            get_history_db_path(),
            retention_days=HISTORY_RETENTION_DAYS,
        )
        self.history_session_id = None
        self._history_capture_reply = False
        self.session = QwenSession(self.active_project_root)
        self._busy = False
        self._pending_message = None

        self._bind_session(self.session)

    def _load_last_active_project(self):
        saved_path = str(
            self.settings.value("last_active_project", "") or ""
        ).strip()

        if not saved_path:
            return None

        saved_root = Path(saved_path)
        if saved_root.exists() and saved_root.is_dir():
            return saved_root

        self.settings.remove("last_active_project")
        return None

    def _save_last_active_project(self, selected_root):
        self.settings.setValue(
            "last_active_project",
            str(Path(selected_root)),
        )
        self.settings.sync()

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
        self.history_session_id = None
        self._history_capture_reply = False
        self._save_last_active_project(selected_root)
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

    @Slot(result=str)
    def get_active_project(self):
        if self.active_project_root is None:
            return ""
        return str(self.active_project_root)

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

    def _ensure_history_session(self):
        if self.history_session_id is None:
            project_path = (
                str(self.active_project_root)
                if self.active_project_root is not None
                else ""
            )
            self.history_session_id = self.history.create_session(project_path)
        return self.history_session_id

    @Slot(str)
    def list_history(self, query=""):
        try:
            payload = {
                "retention_days": HISTORY_RETENTION_DAYS,
                "sessions": self.history.list_sessions(query),
            }
            self.history_sessions_ready.emit(
                json.dumps(payload, ensure_ascii=False)
            )
        except Exception as error:
            self.error_ready.emit(f"Sohbet geçmişi okunamadı: {error}")

    @Slot(str)
    def get_history_session(self, session_id):
        try:
            payload = self.history.get_session(session_id) or {}
            self.history_session_ready.emit(
                json.dumps(payload, ensure_ascii=False)
            )
        except Exception as error:
            self.error_ready.emit(f"Sohbet geçmişi açılamadı: {error}")

    @Slot(str)
    def delete_history_session(self, session_id):
        try:
            deleted = self.history.delete_session(session_id)
            if deleted and str(session_id) == str(self.history_session_id or ""):
                self.history_session_id = None
                self._history_capture_reply = False
            self.history_action_ready.emit(
                json.dumps(
                    {
                        "action": "delete_session",
                        "deleted": 1 if deleted else 0,
                    },
                    ensure_ascii=False,
                )
            )
            self.list_history("")
        except Exception as error:
            self.error_ready.emit(f"Sohbet geçmişi silinemedi: {error}")

    @Slot(str)
    def delete_history_before(self, cutoff_iso):
        try:
            deleted = self.history.delete_before(cutoff_iso)
            if (
                self.history_session_id is not None
                and self.history.get_session(self.history_session_id) is None
            ):
                self.history_session_id = None
                self._history_capture_reply = False
            self.history_action_ready.emit(
                json.dumps(
                    {
                        "action": "delete_before",
                        "deleted": deleted,
                    },
                    ensure_ascii=False,
                )
            )
            self.list_history("")
        except (OSError, ValueError, sqlite3.Error) as error:
            self.error_ready.emit(f"Sohbet geçmişi silinemedi: {error}")

    @Slot(str)
    def send_message(self, message):
        message = str(message or "").strip()
        if not message:
            self.error_ready.emit("Boş mesaj gönderilemez.")
            return

        if self._busy:
            self.error_ready.emit("Qwen Code şu anda başka bir mesaja cevap veriyor.")
            return

        history_session_id = self._ensure_history_session()
        self.history.add_message(history_session_id, "user", message)
        self._history_capture_reply = True

        if not self.session.is_ready:
            self._pending_message = message
            return

        self._busy = True
        if not self.session.submit_prompt(message):
            self._busy = False
            self._history_capture_reply = False

    def _on_reply(self, text):
        self._busy = False
        if self._history_capture_reply and self.history_session_id is not None:
            self.history.add_message(
                self.history_session_id,
                "assistant",
                text,
            )
        self._history_capture_reply = False
        self.reply_ready.emit(text)

    def _on_error(self, text):
        self._busy = False
        self._history_capture_reply = False
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
