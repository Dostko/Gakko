from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ..qwen_ayarlar import (
    MAX_PDF_TEXT_CHARS,
    MAX_PDF_VISION_PAGES,
    MIN_PDF_TEXT_CHARS,
    PDF_EXTENSIONS,
    PDF_RENDER_MAX_HEIGHT,
    PDF_RENDER_WIDTH,
    VISION_CONTEXT_SIZE,
    VISION_MODEL,
    _CANCELLED,
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
                "[PDF METİN] pdftotext bulunamadı; "
                "görsel yola geçiliyor.",
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
                        "[PDF METİN] çıktı dosyası oluşmadı; "
                        "görsel yola geçiliyor.",
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
                        "[PDF METİN] anlamlı metin çıkmadı; "
                        "görsel yola geçiliyor.",
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
                "[PDF METİN] pdftotext zaman aşımına uğradı; "
                "görsel yola geçiliyor.",
                flush=True,
            )
            return ""

        except Exception as error:
            print(
                f"[PDF METİN] {type(error).__name__}: {error} | "
                "görsel yola geçiliyor.",
                flush=True,
            )
            return ""

    def _render_pdf_pages(self, file_path, output_dir):
        from PySide6.QtCore import QSize
        from PySide6.QtPdf import QPdfDocument

        document = QPdfDocument()

        try:
            document.load(str(file_path))
            page_count = int(document.pageCount())

            if page_count <= 0:
                raise RuntimeError(
                    f"PDF açılamadı veya sayfa bulunamadı: {file_path}"
                )

            page_limit = min(
                page_count,
                MAX_PDF_VISION_PAGES,
            )

            image_paths = []

            for page_index in range(page_limit):
                if self._stopping:
                    break

                page_size = document.pagePointSize(page_index)
                page_width = float(page_size.width())
                page_height = float(page_size.height())

                if page_width <= 0 or page_height <= 0:
                    render_width = PDF_RENDER_WIDTH
                    render_height = PDF_RENDER_MAX_HEIGHT

                else:
                    render_width = PDF_RENDER_WIDTH

                    render_height = max(
                        1,
                        round(
                            render_width
                            * (page_height / page_width)
                        ),
                    )

                    if render_height > PDF_RENDER_MAX_HEIGHT:
                        scale = (
                            PDF_RENDER_MAX_HEIGHT
                            / render_height
                        )

                        render_width = max(
                            1,
                            round(
                                render_width * scale
                            ),
                        )

                        render_height = PDF_RENDER_MAX_HEIGHT

                image = document.render(
                    page_index,
                    QSize(
                        render_width,
                        render_height,
                    ),
                )

                if image.isNull():
                    raise RuntimeError(
                        "PDF sayfası görüntüye çevrilemedi: "
                        f"{page_index + 1}"
                    )

                output_path = (
                    output_dir
                    / f"page_{page_index + 1:04d}.png"
                )

                if not image.save(
                    str(output_path),
                    "PNG",
                ):
                    raise RuntimeError(
                        "PDF sayfa görüntüsü kaydedilemedi: "
                        f"{page_index + 1}"
                    )

                image_paths.append(output_path)

            return image_paths, page_count

        finally:
            try:
                document.close()
            except Exception:
                pass

    def _analyze_pdf_visually(
        self,
        file_path,
        user_request,
    ):
        try:
            if not file_path.exists():
                return (
                    f"[PDF ANALİZ HATA] "
                    f"Dosya bulunamadı: {file_path}"
                )

            if not file_path.is_file():
                return (
                    f"[PDF ANALİZ HATA] "
                    f"Yol bir dosya değil: {file_path}"
                )

            if self._stopping:
                return "[PDF ANALİZ DURDU]"

            with tempfile.TemporaryDirectory(
                prefix="gakko-pdf-vision-"
            ) as temp_dir:
                image_paths, page_count = (
                    self._render_pdf_pages(
                        file_path,
                        Path(temp_dir),
                    )
                )

                if not image_paths:
                    return "[PDF ANALİZ DURDU]"

                print(
                    f"[QWEN PDF GÖRSEL İSTEDİ] {file_path} | "
                    f"sayfa={page_count} | "
                    f"işlenecek={len(image_paths)}",
                    flush=True,
                )

                page_note = ""

                if page_count > len(image_paths):
                    page_note = (
                        f"\nBelge {page_count} sayfa; bu istekte "
                        f"ilk {len(image_paths)} sayfa görüntü olarak "
                        "işleniyor. Kalan sayfaları okumuş gibi davranma."
                    )

                vision_prompt = (
                    "Bu görüntüler aynı PDF belgesinin sayfalarıdır ve "
                    "sıraları korunmuştur.\n"
                    "GAKKO'nun ana modeli için belge bağlamı üret.\n"
                    "Kullanıcının isteğini dikkate al.\n"
                    "Metin, tablo, başlık ve görselleri yalnız "
                    "doğrulanabildiği ölçüde aktar.\n"
                    "Görünen yazıları mümkün olduğunca doğru oku.\n"
                    "Nihai kullanıcı cevabını verme; yalnız PDF bağlamı üret."
                    f"{page_note}\n\n"
                    "Kullanıcı isteği:\n"
                    f"{user_request}"
                )

                response = self._chat(
                    model=VISION_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": vision_prompt,
                            "images": [
                                str(path)
                                for path in image_paths
                            ],
                        }
                    ],
                    stream=False,
                    options={
                        "num_ctx": VISION_CONTEXT_SIZE,
                    },
                )

                if response is _CANCELLED:
                    return "[PDF ANALİZ DURDU]"

                content = (
                    response.message.content or ""
                ).strip()

                if not content:
                    return (
                        "[PDF ANALİZ HATA] "
                        f"{VISION_MODEL} boş çıktı üretti: {file_path}"
                    )

                return content

        except Exception as error:
            return (
                "[PDF ANALİZ HATA] "
                f"{type(error).__name__}: {error}"
            )
