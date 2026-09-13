import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from Sohbet_Bilesenleri.proje_dosya_yardimcilari import PROJECT_ROOT


DEFAULT_RECORDS_ROOT = PROJECT_ROOT / "GAKKO_YUVA" / "Kayitlar"
MAX_RECORD_BYTES = 2 * 1024 * 1024


class KayitlarKoprusu(QObject):
    records_list_ready = Signal(str)
    record_ready = Signal(str)
    record_action_ready = Signal(str)
    error_ready = Signal(str)

    def __init__(self, records_root=None):
        super().__init__()
        self.records_root = Path(records_root or DEFAULT_RECORDS_ROOT).resolve()

    @staticmethod
    def _size_text(size):
        size = max(0, int(size or 0))
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    @staticmethod
    def _title(path):
        return path.stem.replace("_", " ").strip() or path.name

    def _target(self, filename):
        raw_name = str(filename or "").strip()
        if not raw_name:
            raise ValueError("Kayıt adı boş.")

        safe_name = Path(raw_name).name
        if safe_name != raw_name or Path(safe_name).suffix.lower() != ".md":
            raise ValueError("Geçersiz kayıt adı.")

        target = (self.records_root / safe_name).resolve()
        if target.parent != self.records_root:
            raise ValueError("Kayıtlar klasörü dışındaki dosyaya erişilemez.")
        return target

    def _record_meta(self, path):
        stat = path.stat()
        return {
            "name": path.name,
            "title": self._title(path),
            "updated_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
            "size": int(stat.st_size),
            "size_text": self._size_text(stat.st_size),
        }

    @Slot(str)
    def list_records(self, query=""):
        query_text = str(query or "").strip().casefold()
        records = []

        try:
            if self.records_root.exists():
                for path in self.records_root.glob("*.md"):
                    if not path.is_file() or path.is_symlink():
                        continue

                    resolved = path.resolve()
                    if resolved.parent != self.records_root:
                        continue

                    if query_text:
                        try:
                            size = path.stat().st_size
                            content = (
                                path.read_text(encoding="utf-8-sig")
                                if size <= MAX_RECORD_BYTES
                                else ""
                            )
                        except OSError:
                            content = ""
                        haystack = f"{path.name}\n{content}".casefold()
                        if query_text not in haystack:
                            continue

                    records.append(self._record_meta(path))

            records.sort(
                key=lambda item: str(item.get("updated_at") or ""),
                reverse=True,
            )
            self.records_list_ready.emit(
                json.dumps({"records": records}, ensure_ascii=False)
            )
        except (OSError, ValueError) as error:
            self.error_ready.emit(f"Kayıtlar okunamadı: {error}")

    @Slot(str)
    def get_record(self, filename):
        try:
            target = self._target(filename)
            if not target.exists() or not target.is_file():
                raise FileNotFoundError("Seçilen kayıt bulunamadı.")

            stat = target.stat()
            if stat.st_size > MAX_RECORD_BYTES:
                raise ValueError("Kayıt görüntüleme sınırını aşıyor.")

            payload = self._record_meta(target)
            payload["content"] = target.read_text(encoding="utf-8-sig")
            self.record_ready.emit(json.dumps(payload, ensure_ascii=False))
        except (OSError, ValueError) as error:
            self.error_ready.emit(f"Kayıt açılamadı: {error}")

    @Slot(str)
    def delete_record(self, filename):
        try:
            target = self._target(filename)
            if not target.exists() or not target.is_file():
                raise FileNotFoundError("Seçilen kayıt bulunamadı.")

            target.unlink()
            self.record_action_ready.emit(
                json.dumps(
                    {"action": "delete", "deleted": 1, "name": target.name},
                    ensure_ascii=False,
                )
            )
        except (OSError, ValueError) as error:
            self.error_ready.emit(f"Kayıt silinemedi: {error}")
