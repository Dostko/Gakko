import base64
import binascii
import json
import tempfile
import uuid
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog

from Sohbet_Bilesenleri.proje_dosya_yardimcilari import (
    PROJECT_ROOT,
    list_project_directory,
)


PROJELER_YONTEMI = (
    PROJECT_ROOT
    / "GAKKO_YUVA"
    / "Projeler"
    / "Projelendirme"
    / "Calisma_Yonu.md"
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


class SohbetGezgini:
    def __init__(self, bridge):
        self.bridge = bridge
        # Aktif proje değişimi (ve oturum yeniden başlatma) aç/kapa anahtarı.
        # True  -> klasör seçince mevcut davranış: aktif proje değişir + oturum
        #         yeniden başlar (_activate_project).
        # False -> sadece klasör seçilir; aktif proje değiştirilmez, oturum
        #         yeniden başlatılmaz (yalnızca seçim bildirilir).
        # Varsayılan mevcut davranışı korur.
        self.activate_projects = True

    def select_project_folder(self):
        if not self.bridge._project_change_allowed():
            return

        selected_path = QFileDialog.getExistingDirectory(
            QApplication.activeWindow(),
            "Proje Aç",
            str(PROJECT_ROOT),
        )

        selected_path = str(selected_path or "").strip()
        if not selected_path:
            return

        if self.activate_projects:
            self.bridge._activate_project(
                Path(selected_path),
                PROJELER_YONTEMI,
            )
        else:
            # Sadece seçilen kökü bildir; aktif proje değiştirilmez, oturum
            # yeniden başlatılmaz.
            self.bridge.project_browser_selected.emit(selected_path)

    def select_file_browser_folder(self):
        selected_path = QFileDialog.getExistingDirectory(
            QApplication.activeWindow(),
            "Dosya - Klasör Aç",
            str(self.bridge.file_browser_root or PROJECT_ROOT),
        )

        selected_path = str(selected_path or "").strip()
        if not selected_path:
            return

        selected_root = Path(selected_path)
        if not selected_root.exists() or not selected_root.is_dir():
            self.bridge.error_ready.emit("Seçilen klasör geçerli değil.")
            return

        self.bridge.file_browser_root = selected_root
        self.bridge.file_browser_project_selected.emit(str(selected_root))

    def emit_chat_files(self, selected_paths):
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

        self.bridge.chat_files_selected.emit(
            json.dumps({"files": files}, ensure_ascii=False)
        )

    def select_chat_files(self):
        if self.bridge._busy:
            self.bridge.error_ready.emit(
                "GAKKO şu anda başka bir mesaja cevap veriyor."
            )
            return

        selected_paths, _ = QFileDialog.getOpenFileNames(
            QApplication.activeWindow(),
            "Dosya veya görsel ekle",
            str(Path.home()),
            "Tüm dosyalar (*.*)",
        )

        self.emit_chat_files(selected_paths)

    def add_chat_files(self, paths_json):
        if self.bridge._busy:
            self.bridge.error_ready.emit(
                "GAKKO şu anda başka bir mesaja cevap veriyor."
            )
            return

        try:
            selected_paths = json.loads(str(paths_json or "[]"))
        except json.JSONDecodeError:
            self.bridge.error_ready.emit("Sürüklenen dosya listesi okunamadı.")
            return

        if not isinstance(selected_paths, list):
            self.bridge.error_ready.emit("Sürüklenen dosya listesi geçerli değil.")
            return

        self.emit_chat_files(selected_paths[:1])

    def cleanup_clipboard_files(self, paths=None):
        targets = (
            set(self.bridge._clipboard_temp_files)
            if paths is None
            else {str(path) for path in paths}
        )

        for raw_path in targets:
            try:
                Path(raw_path).unlink(missing_ok=True)
            except OSError:
                pass
            self.bridge._clipboard_temp_files.discard(raw_path)
            self.bridge._clipboard_inflight_files.discard(raw_path)

    def cleanup_inflight_clipboard_files(self):
        if not self.bridge._clipboard_inflight_files:
            return
        self.cleanup_clipboard_files(self.bridge._clipboard_inflight_files)

    def add_clipboard_image(self, data_url):
        if self.bridge._busy:
            self.bridge.error_ready.emit(
                "GAKKO şu anda başka bir mesaja cevap veriyor."
            )
            return

        try:
            _mime_type, suffix, raw = _decode_clipboard_image_data_url(data_url)

            temp_root = Path(tempfile.gettempdir()) / "Gakko" / "Pano"
            temp_root.mkdir(parents=True, exist_ok=True)
            target = temp_root / f"gakko_pano_{uuid.uuid4().hex}{suffix}"
            target.write_bytes(raw)
        except (OSError, ValueError) as error:
            self.bridge.error_ready.emit(f"Pano görseli eklenemedi: {error}")
            return

        self.bridge._clipboard_temp_files.add(str(target))
        self.emit_chat_files([str(target)])

    def start_new_project(self):
        if not self.bridge._project_change_allowed():
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
            self.bridge.error_ready.emit("Seçilen proje klasörü geçerli değil.")
            return

        self.bridge._activate_project(
            selected_root,
            PROJELER_YONTEMI,
        )

    def get_active_project(self):
        if self.bridge.active_project_root is None:
            return ""
        return str(self.bridge.active_project_root)

    def list_file_browser_directory(self, relative_path):
        if self.bridge.file_browser_root is None:
            return

        try:
            payload = list_project_directory(
                self.bridge.file_browser_root,
                relative_path,
            )
        except (OSError, ValueError) as error:
            self.bridge.error_ready.emit(f"Dosya klasörü okunamadı: {error}")
            return

        self.bridge.file_browser_directory_ready.emit(
            json.dumps(payload, ensure_ascii=False)
        )

    def read_file_browser_file(self, relative_path):
        if self.bridge.file_browser_root is None:
            return

        root = Path(self.bridge.file_browser_root).resolve()
        relative = str(relative_path or "").replace("\\", "/").strip("/")
        target = root.joinpath(
            *([part for part in relative.split("/") if part] or [])
        ).resolve()

        if target != root and not target.is_relative_to(root):
            self.bridge.error_ready.emit("Dosya klasörü dışındaki dosyalar açılamaz.")
            return

        if not target.exists() or not target.is_file():
            self.bridge.error_ready.emit("Seçilen dosya bulunamadı.")
            return

        try:
            raw = target.read_bytes()
        except OSError as error:
            self.bridge.error_ready.emit(f"Dosya okunamadı: {error}")
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
                self.bridge.error_ready.emit("Görsel, dosya okuma alanı için çok büyük.")
                return

            encoded = base64.b64encode(raw).decode("ascii")
            payload = {
                "kind": "image",
                "path": relative,
                "name": target.name,
                "mime": image_mime,
                "data_url": f"data:{image_mime};base64,{encoded}",
            }
            self.bridge.file_browser_file_ready.emit(
                json.dumps(payload, ensure_ascii=False)
            )
            return

        if b"\x00" in raw[:8192]:
            self.bridge.error_ready.emit(
                "Bu dosya desteklenen bir metin veya görsel dosyası değil."
            )
            return

        if len(raw) > 2 * 1024 * 1024:
            self.bridge.error_ready.emit("Dosya okuma alanı için çok büyük.")
            return

        content = raw.decode("utf-8-sig", errors="replace")
        payload = {
            "kind": "text",
            "path": relative,
            "name": target.name,
            "content": content,
        }
        self.bridge.file_browser_file_ready.emit(
            json.dumps(payload, ensure_ascii=False)
        )
