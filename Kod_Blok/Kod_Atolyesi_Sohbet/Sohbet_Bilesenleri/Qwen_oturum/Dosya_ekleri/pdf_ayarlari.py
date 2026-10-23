from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ..qwen_ayarlar import (
    MAX_PDF_TEXT_CHARS,
    MIN_PDF_TEXT_CHARS,
    PDF_EXTENSIONS,
)


class PdfAyarlariMixin:
    def _pdf_path_from_attachment_line(self, line):
        return self._attachment_path_from_line(line, PDF_EXTENSIONS)

    def _extract_pdf_text(self, file_path):
        """
        PDF'yi yorumlamaz.
        Yalnız pdftotext aracını teknik taşıma katmanı olarak kullanıp
        çıkarılabilen metni UTF-8 olarak döndürür.
        """
        pdftotext_exe = shutil.which("pdftotext")

        if not pdftotext_exe:
            print(
                "[PDF METİN] pdftotext bulunamadı.",
                flush=True,
            )
            return ""

        try:
            with tempfile.TemporaryDirectory(
                prefix="gakko-pdf-text-"
            ) as temp_dir:
                output_path = Path(temp_dir) / "pdf_metni.txt"

                completed = subprocess.run(
                    [
                        pdftotext_exe,
                        "-layout",
                        "-enc",
                        "UTF-8",
                        str(file_path),
                        str(output_path),
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                    check=False,
                )

                if completed.returncode != 0:
                    detail = (
                        completed.stderr
                        or completed.stdout
                        or "bilinmeyen pdftotext hatası"
                    ).strip()

                    print(
                        f"[PDF METİN] çıkarılamadı: {detail}",
                        flush=True,
                    )

                    return ""

                if not output_path.exists():
                    print(
                        "[PDF METİN] çıktı dosyası oluşmadı.",
                        flush=True,
                    )
                    return ""

                extracted = output_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).strip()

                compact_length = len(
                    "".join(extracted.split())
                )

                if compact_length < MIN_PDF_TEXT_CHARS:
                    print(
                        "[PDF METİN] anlamlı metin çıkmadı.",
                        flush=True,
                    )
                    return ""

                if len(extracted) > MAX_PDF_TEXT_CHARS:
                    extracted = (
                        extracted[:MAX_PDF_TEXT_CHARS]
                        + "\n\n"
                        "[PDF METİN SINIRI] Belgenin devamı bu istekte "
                        "bağlama alınmadı."
                    )

                print(
                    f"[QWEN PDF METNİ HAZIR] {file_path}",
                    flush=True,
                )

                return extracted

        except subprocess.TimeoutExpired:
            print(
                "[PDF METİN] pdftotext zaman aşımına uğradı.",
                flush=True,
            )
            return ""

        except Exception as error:
            print(
                f"[PDF METİN] {type(error).__name__}: {error}",
                flush=True,
            )
            return ""