import base64
import binascii
import json
import sqlite3
import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal, Slot
from PySide6.QtWidgets import QApplication, QFileDialog

from Sohbet_Bilesenleri.proje_dosya_yardimcilari import (
    PROJECT_ROOT,
    build_attachment_history_message,
    build_attachment_prompt,
    list_project_directory,
)
from Sohbet_Bilesenleri.qwen_oturumu import QwenSession
from Sohbet_Bilesenleri.sohbet_gecmisi import (
    ChatHistoryStore,
    HISTORY_RETENTION_DAYS,
    get_history_db_path,
)


PROJELER_YONTEMI = (
    PROJECT_ROOT
    / "GAKKO_YUVA"
    / "Calisma_Yontemleri"
    / "projeler.md"
)


CHAT_IMAGE_EXTENSIONS = frozenset({
    ".bmp",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".tif",
    ".tiff",
    ".webp",
})

GORSELLER_ROOT = PROJECT_ROOT / "Gorseller"



def _decode_clipboard_image_data_url(data_url):
    value = str(data_url or "").strip()
    header, separator, payload = value.partition(",")

    if not separator or not header.lower().startswith("data:image/"):
        raise ValueError("Pano görsel verisi geçerli değil.")

    parts = header[5:].split(";")
    mime_type = parts[0].strip().lower()
    if "base64" not in {part.strip().lower() for part in parts[1:]}:
        raise ValueError("Pano görseli Base64 biçiminde değil.")

    mime_extensions = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }
    suffix = mime_extensions.get(mime_type)
    if suffix is None:
        raise ValueError(f"Desteklenmeyen pano görsel türü: {mime_type}")

    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Pano görseli çözümlenemedi.") from error

    if not raw:
        raise ValueError("Pano görseli boş.")

    if len(raw) > 12 * 1024 * 1024:
        raise ValueError("Pano görseli 12 MB sınırını aşıyor.")

    return mime_type, suffix, raw


class ChatBridge(QObject):
    reply_ready = Signal(str)
    error_ready = Signal(str)
    connection_ready = Signal()
    project_selected = Signal(str)
    file_browser_project_selected = Signal(str)
    file_browser_directory_ready = Signal(str)
    file_browser_file_ready = Signal(str)
    history_sessions_ready = Signal(str)
    history_session_ready = Signal(str)
    history_action_ready = Signal(str)
    chat_files_selected = Signal(str)
    context_remaining_ready = Signal(float)
    generation_cancelled = Signal()
    tool_activity = Signal(str)

    def __init__(self):
        super().__init__()
        self.settings = QSettings("Gakko", "Gakko")
        self.active_project_root = self._load_last_active_project()
        self.file_browser_root = None
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
        session.cancelled.connect(self._on_cancelled)
        session.context_remaining.connect(self._on_context_remaining)
        session.tool_activity.connect(self._on_tool_activity)

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
            self.error_ready.emit("Mevcut GAKKO oturumu kapatılamadı.")
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
                "GAKKO şu anda başka bir mesaja cevap veriyor."
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
            PROJELER_YONTEMI,
        )

    @Slot()
    def select_file_browser_folder(self):
        selected_path = QFileDialog.getExistingDirectory(
            QApplication.activeWindow(),
            "Dosya - Klasör Aç",
            str(self.file_browser_root or PROJECT_ROOT),
        )

        selected_path = str(selected_path or "").strip()
        if not selected_path:
            return

        selected_root = Path(selected_path)
        if not selected_root.exists() or not selected_root.is_dir():
            self.error_ready.emit("Seçilen klasör geçerli değil.")
            return

        self.file_browser_root = selected_root
        self.file_browser_project_selected.emit(str(selected_root))

    def _emit_chat_files(self, selected_paths):
        files = []
        image_mime_types = {
            ".bmp": "image/bmp",
            ".gif": "image/gif",
            ".ico": "image/x-icon",
            ".jpeg": "image/jpeg",
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".tif": "image/tiff",
            ".tiff": "image/tiff",
            ".webp": "image/webp",
        }

        for selected_path in selected_paths:
            path = Path(str(selected_path or "").strip())
            if not path.exists() or not path.is_file():
                continue

            suffix = path.suffix.lower()
            is_image = suffix in CHAT_IMAGE_EXTENSIONS

            if is_image:
                try:
                    GORSELLER_ROOT.mkdir(parents=True, exist_ok=True)
                    source = path.resolve()
                    image_root = GORSELLER_ROOT.resolve()

                    if source != image_root and not source.is_relative_to(image_root):
                        target = GORSELLER_ROOT / path.name
                        if target.exists():
                            target = GORSELLER_ROOT / (
                                f"{path.stem}_{uuid.uuid4().hex[:8]}{path.suffix.lower()}"
                            )
                        shutil.copy2(path, target)
                        path = target
                except OSError as error:
                    self.error_ready.emit(f"Görsel Gorseller klasörüne alınamadı: {error}")
                    continue

            item = {
                "path": str(path),
                "name": path.name,
                "type": "image" if is_image else "file",
            }

            if is_image:
                mime_type = image_mime_types.get(suffix)
                try:
                    file_size = path.stat().st_size
                except OSError:
                    file_size = 0

                if mime_type and 0 < file_size <= 12 * 1024 * 1024:
                    try:
                        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                        item["data_url"] = f"data:{mime_type};base64,{encoded}"
                    except OSError:
                        pass

            files.append(item)

        if not files:
            return

        self.chat_files_selected.emit(
            json.dumps({"files": files}, ensure_ascii=False)
        )

    @Slot()
    def select_chat_files(self):
        if self._busy:
            self.error_ready.emit(
                "GAKKO şu anda başka bir mesaja cevap veriyor."
            )
            return

        selected_paths, _ = QFileDialog.getOpenFileNames(
            QApplication.activeWindow(),
            "Dosya veya görsel ekle",
            str(Path.home()),
            "Tüm dosyalar (*.*)",
        )

        self._emit_chat_files(selected_paths)

    @Slot(str)
    def add_chat_files(self, paths_json):
        if self._busy:
            self.error_ready.emit(
                "GAKKO şu anda başka bir mesaja cevap veriyor."
            )
            return

        try:
            selected_paths = json.loads(str(paths_json or "[]"))
        except json.JSONDecodeError:
            self.error_ready.emit("Sürüklenen dosya listesi okunamadı.")
            return

        if not isinstance(selected_paths, list):
            self.error_ready.emit("Sürüklenen dosya listesi geçerli değil.")
            return

        self._emit_chat_files(selected_paths[:1])


    @Slot(str)
    def add_clipboard_image(self, data_url):
        if self._busy:
            self.error_ready.emit(
                "GAKKO şu anda başka bir mesaja cevap veriyor."
            )
            return

        try:
            _mime_type, suffix, raw = _decode_clipboard_image_data_url(data_url)

            GORSELLER_ROOT.mkdir(parents=True, exist_ok=True)
            target = GORSELLER_ROOT / f"gakko_pano_{uuid.uuid4().hex}{suffix}"
            target.write_bytes(raw)
        except (OSError, ValueError) as error:
            self.error_ready.emit(f"Pano görseli eklenemedi: {error}")
            return

        self._emit_chat_files([str(target)])

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

        self._activate_project(
            selected_root,
            PROJELER_YONTEMI,
        )

    @Slot(result=str)
    def get_active_project(self):
        if self.active_project_root is None:
            return ""
        return str(self.active_project_root)

    @Slot(str)
    def list_file_browser_directory(self, relative_path):
        if self.file_browser_root is None:
            return

        try:
            payload = list_project_directory(
                self.file_browser_root,
                relative_path,
            )
        except (OSError, ValueError) as error:
            self.error_ready.emit(f"Dosya klasörü okunamadı: {error}")
            return

        self.file_browser_directory_ready.emit(
            json.dumps(payload, ensure_ascii=False)
        )

    @Slot(str)
    def read_file_browser_file(self, relative_path):
        if self.file_browser_root is None:
            return

        root = Path(self.file_browser_root).resolve()
        relative = str(relative_path or "").replace("\\", "/").strip("/")
        target = root.joinpath(
            *([part for part in relative.split("/") if part] or [])
        ).resolve()

        if target != root and not target.is_relative_to(root):
            self.error_ready.emit("Dosya klasörü dışındaki dosyalar açılamaz.")
            return

        if not target.exists() or not target.is_file():
            self.error_ready.emit("Seçilen dosya bulunamadı.")
            return

        try:
            raw = target.read_bytes()
        except OSError as error:
            self.error_ready.emit(f"Dosya okunamadı: {error}")
            return

        image_mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".ico": "image/x-icon",
        }
        suffix = target.suffix.lower()
        image_mime = image_mime_types.get(suffix)

        if image_mime is not None:
            if len(raw) > 12 * 1024 * 1024:
                self.error_ready.emit("Görsel, dosya okuma alanı için çok büyük.")
                return

            encoded = base64.b64encode(raw).decode("ascii")
            payload = {
                "kind": "image",
                "path": relative,
                "name": target.name,
                "mime": image_mime,
                "data_url": f"data:{image_mime};base64,{encoded}",
            }
            self.file_browser_file_ready.emit(
                json.dumps(payload, ensure_ascii=False)
            )
            return

        if b"\x00" in raw[:8192]:
            self.error_ready.emit("Bu dosya desteklenen bir metin veya görsel dosyası değil.")
            return

        if len(raw) > 2 * 1024 * 1024:
            self.error_ready.emit("Dosya okuma alanı için çok büyük.")
            return

        content = raw.decode("utf-8-sig", errors="replace")
        payload = {
            "kind": "text",
            "path": relative,
            "name": target.name,
            "content": content,
        }
        self.file_browser_file_ready.emit(
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

    def _send_chat_prompt(self, prompt, history_message):
        prompt = str(prompt or "").strip()
        history_message = str(history_message or "").strip()

        if not prompt:
            self.error_ready.emit("Boş mesaj gönderilemez.")
            return

        if self._busy:
            self.error_ready.emit("GAKKO şu anda başka bir mesaja cevap veriyor.")
            return

        history_session_id = self._ensure_history_session()
        self.history.add_message(
            history_session_id,
            "user",
            history_message or prompt,
        )
        self._history_capture_reply = True

        if not self.session.is_ready:
            self._pending_message = prompt
            return

        self._busy = True
        if not self.session.submit_prompt(prompt):
            self._busy = False
            self._history_capture_reply = False

    @Slot()
    def reset_qwen_context(self):
        if self._busy:
            self.error_ready.emit(
                "GAKKO şu anda başka bir mesaja cevap veriyor."
            )
            return

        if not self.session.is_ready:
            self.error_ready.emit("GAKKO henüz hazır değil.")
            return

        self.session.reset_context()

    @Slot()
    def cancel_generation(self):
        if self._pending_message is not None:
            self._pending_message = None
            self._history_capture_reply = False
            self._busy = False
            self.generation_cancelled.emit()
            return

        if not self._busy:
            return

        if not self.session.cancel_current():
            self.error_ready.emit("Aktif Qwen isteği durdurulamadı.")

    @Slot(str)
    def send_message(self, message):
        message = str(message or "").strip()
        self._send_chat_prompt(message, message)

    @Slot(str, str)
    def send_message_with_attachments(self, message, attachments_json):
        try:
            raw_items = json.loads(str(attachments_json or "[]"))
        except json.JSONDecodeError:
            self.error_ready.emit("Ekli dosya listesi okunamadı.")
            return

        if not isinstance(raw_items, list):
            self.error_ready.emit("Ekli dosya listesi geçerli değil.")
            return

        file_paths = []
        seen = set()
        for item in raw_items:
            raw_path = item.get("path", "") if isinstance(item, dict) else item
            raw_path = str(raw_path or "").strip()
            if not raw_path:
                continue

            path = Path(raw_path)
            try:
                valid = path.exists() and path.is_file()
            except OSError:
                valid = False

            if not valid:
                continue

            key = str(path).casefold()
            if key in seen:
                continue
            seen.add(key)
            file_paths.append(str(path))

        if not file_paths:
            self.error_ready.emit("Seçilen ek dosyalar bulunamadı.")
            return

        prompt = build_attachment_prompt(message, file_paths)
        history_message = build_attachment_history_message(message, file_paths)
        self._send_chat_prompt(prompt, history_message)

    def _on_tool_activity(self, payload):
        self.tool_activity.emit(str(payload or ""))

    def _on_context_remaining(self, value):
        self.context_remaining_ready.emit(float(value))

    def _on_tool_activity(self, payload):
        self.tool_activity.emit(str(payload or ""))

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

    def _on_cancelled(self):
        self._busy = False
        self._history_capture_reply = False
        self.generation_cancelled.emit()

    def close(self):
        self._pending_message = None
        self._history_capture_reply = False
        self.session.stop()
        if self.session.wait(10000):
            return True

        self.error_ready.emit("Qwen oturumu güvenli biçimde kapatılamadı.")
        return False
