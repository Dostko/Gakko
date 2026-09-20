import json
import tempfile
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

from PySide6.QtCore import QObject, QSettings, Signal, Slot

from Sohbet_Bilesenleri.ekran_gorunum import EkranGorunum
from Sohbet_Bilesenleri.proje_dosya_yardimcilari import (
    build_attachment_history_message,
    build_attachment_prompt,
)
from Sohbet_Bilesenleri.qwen_oturumu import QwenSession
from Sohbet_Bilesenleri.sohbet_gecmisi import (
    ChatHistoryStore,
    HISTORY_RETENTION_DAYS,
    get_history_db_path,
)


def _load_history_bridge_class():
    helper_path = (
        Path(__file__).with_name("sohbet_koprusu")
        / "sohbet_gecmisi_koprusu.py"
    )
    spec = spec_from_file_location("gakko_sohbet_gecmisi_koprusu", helper_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Sohbet geçmişi köprüsü yüklenemedi: {helper_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SohbetGecmisiKoprusu


def _load_chat_navigator_class():
    helper_path = (
        Path(__file__).with_name("sohbet_koprusu")
        / "sohbet_gezgini.py"
    )
    spec = spec_from_file_location("gakko_sohbet_gezgini", helper_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Sohbet gezgini yüklenemedi: {helper_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SohbetGezgini


def _load_pagination_class():
    helper_path = (
        Path(__file__).with_name("sohbet_koprusu")
        / "sayfalama_teknikleri.py"
    )
    spec = spec_from_file_location("gakko_sayfalama_teknikleri", helper_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Sayfalama teknikleri yüklenemedi: {helper_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SayfalamaTeknikleri


SohbetGecmisiKoprusu = _load_history_bridge_class()
SohbetGezgini = _load_chat_navigator_class()
SayfalamaTeknikleri = _load_pagination_class()

class ChatBridge(QObject):
    reply_ready = Signal(str)
    error_ready = Signal(str)
    connection_ready = Signal()
    project_selected = Signal(str)
    project_browser_selected = Signal(str)
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
    active_chat_ready = Signal(str)

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
        self.history_bridge = SohbetGecmisiKoprusu(self)
        self.sohbet_gezgini = SohbetGezgini(self)
        self.sayfalama = SayfalamaTeknikleri(self)
        self.ekran_gorunum = EkranGorunum()
        self._model_mode = "auto"
        self._generated_images_temp = tempfile.TemporaryDirectory(
            prefix="gakko_uretilen_",
            ignore_cleanup_errors=True,
        )
        self._generated_images_root = Path(
            self._generated_images_temp.name
        )
        self.session = QwenSession(
            self.active_project_root,
            self._generated_images_root,
        )
        self.session.set_model_mode(self._model_mode)
        self._busy = False
        self._pending_message = None
        self._clipboard_temp_files = set()
        self._clipboard_inflight_files = set()

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
                self._cleanup_inflight_clipboard_files()

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

        self.session = QwenSession(
            selected_root,
            self._generated_images_root,
        )
        self.session.set_model_mode(self._model_mode)
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
        self.sohbet_gezgini.select_project_folder()

    @Slot()
    def select_file_browser_folder(self):
        self.sohbet_gezgini.select_file_browser_folder()

    def _emit_chat_files(self, selected_paths):
        self.sohbet_gezgini.emit_chat_files(selected_paths)

    @Slot()
    def select_chat_files(self):
        self.sohbet_gezgini.select_chat_files()

    @Slot(str)
    def add_chat_files(self, paths_json):
        self.sohbet_gezgini.add_chat_files(paths_json)

    def _cleanup_clipboard_files(self, paths=None):
        self.sohbet_gezgini.cleanup_clipboard_files(paths)

    def _cleanup_inflight_clipboard_files(self):
        self.sohbet_gezgini.cleanup_inflight_clipboard_files()

    @Slot(str)
    def add_clipboard_image(self, data_url):
        self.sohbet_gezgini.add_clipboard_image(data_url)

    @Slot(str, result=bool)
    def copy_text_to_clipboard(self, text):
        return self.ekran_gorunum.copy_text_to_clipboard(text)

    @Slot()
    def start_new_project(self):
        self.sohbet_gezgini.start_new_project()

    @Slot(result=str)
    def get_active_project(self):
        return self.sohbet_gezgini.get_active_project()

    @Slot(str)
    def list_file_browser_directory(self, relative_path):
        self.sohbet_gezgini.list_file_browser_directory(relative_path)

    @Slot(str)
    def read_file_browser_file(self, relative_path):
        self.sohbet_gezgini.read_file_browser_file(relative_path)

    @Slot(str)
    def list_history(self, query=""):
        self.history_bridge.list_history(query)

    @Slot(str)
    def get_history_session(self, session_id):
        self.history_bridge.get_history_session(session_id)

    @Slot()
    def load_active_chat(self):
        self.sayfalama.load_active_page()

    @Slot()
    def start_new_chat_page(self):
        self.sayfalama.start_new_page()

    @Slot(str)
    def delete_history_session(self, session_id):
        self.history_bridge.delete_history_session(session_id)

    @Slot(str)
    def delete_history_before(self, cutoff_iso):
        self.history_bridge.delete_history_before(cutoff_iso)

    def _send_chat_prompt(self, prompt, history_message):
        prompt = str(prompt or "").strip()
        history_message = str(history_message or "").strip()

        if not prompt:
            self.error_ready.emit("Boş mesaj gönderilemez.")
            return

        if self._busy:
            self.error_ready.emit("GAKKO şu anda başka bir mesaja cevap veriyor.")
            return

        history_session_id = self.history_bridge.ensure_session()
        self.sayfalama.remember_active_session(history_session_id)
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

    @Slot(str)
    def set_model_mode(self, mode):
        normalized = str(mode or "").strip().casefold()

        if normalized not in {"auto", "normal", "kod"}:
            self.error_ready.emit("Geçersiz model seçimi.")
            return

        self._model_mode = normalized
        self.session.set_model_mode(normalized)

    @Slot()
    def cancel_generation(self):
        if self._pending_message is not None:
            self._pending_message = None
            self._history_capture_reply = False
            self._busy = False
            self._cleanup_inflight_clipboard_files()
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

        if not self._busy:
            self._clipboard_inflight_files.update(
                path for path in file_paths if path in self._clipboard_temp_files
            )

        self._send_chat_prompt(prompt, history_message)

    def _on_tool_activity(self, payload):
        self.tool_activity.emit(str(payload or ""))

    def _on_context_remaining(self, value):
        self.context_remaining_ready.emit(float(value))

    def _on_reply(self, text):
        self._busy = False
        self._cleanup_inflight_clipboard_files()
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
        self._cleanup_inflight_clipboard_files()
        self._history_capture_reply = False
        self.error_ready.emit(text)

    def _on_cancelled(self):
        self._busy = False
        self._cleanup_inflight_clipboard_files()
        self._history_capture_reply = False
        self.generation_cancelled.emit()

    def close(self):
        self._pending_message = None
        self._history_capture_reply = False
        self._cleanup_clipboard_files()
        self.session.stop()
        if self.session.wait(10000):
            self._generated_images_temp.cleanup()
            return True

        self.error_ready.emit("Qwen oturumu güvenli biçimde kapatılamadı.")
        return False
