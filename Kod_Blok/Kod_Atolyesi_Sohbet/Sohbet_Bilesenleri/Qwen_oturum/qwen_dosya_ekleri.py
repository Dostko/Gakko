from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .qwen_ayarlar import (
    IMAGE_EXTENSIONS,
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


class QwenDosyaEkleriMixin:
    def _resolve_attachment_path(self, raw_path):
        value = str(raw_path or "").strip()

        if not value:
            raise ValueError("Dosya yolu boş.")

        path = Path(value).expanduser()

        if not path.is_absolute():
            if self.active_project_root is not None:
                path = Path(self.active_project_root) / path
            else:
                path = Path.cwd() / path

        return path.resolve()

    def _image_path_from_attachment_line(self, line):
        stripped = str(line or "").strip()

        # + dosya ekleme akışı satırı "- @D:/dosya.png" biçiminde üretir.
        # Doğrudan "@D:/dosya.png" biçimini de destekle.
        if stripped.startswith("-"):
            stripped = stripped[1:].lstrip()

        if not stripped.startswith("@"):
            return None

        raw_path = stripped[1:].strip().strip('"').strip("'")

        if not raw_path:
            return None

        # Ek dosya referanslarında boşluklar "\ " olarak kaçırılır.
        raw_path = raw_path.replace("\\ ", " ")

        try:
            file_path = self._resolve_attachment_path(raw_path)
        except Exception:
            return None

        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            return None

        return file_path

    def _analyze_image(self, file_path, user_request):
        try:
            if not file_path.exists():
                return (
                    f"[GÖRSEL ANALİZ HATA] "
                    f"Dosya bulunamadı: {file_path}"
                )

            if not file_path.is_file():
                return (
                    f"[GÖRSEL ANALİZ HATA] "
                    f"Yol bir dosya değil: {file_path}"
                )

            if self._stopping:
                return "[GÖRSEL ANALİZ DURDU]"

            print(
                f"[QWEN GÖRSEL İSTEDİ] {file_path}",
                flush=True,
            )

            vision_prompt = (
                "Bu görseli GAKKO'nun ana modeli için incele.\n"
                "Kullanıcının isteğini dikkate al.\n"
                "Yalnız görselden doğrulanabilen bilgileri aktar.\n"
                "Görünen yazıları mümkün olduğunca doğru oku.\n"
                "Nihai kullanıcı cevabını verme; yalnız görsel bağlamı üret.\n\n"
                "Kullanıcı isteği:\n"
                f"{user_request}"
            )

            response = self._chat(
                model=VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": vision_prompt,
                        "images": [str(file_path)],
                    }
                ],
                stream=False,
                options={"num_ctx": VISION_CONTEXT_SIZE},
            )

            if response is _CANCELLED:
                return "[GÖRSEL ANALİZ DURDU]"

            content = (
                response.message.content or ""
            ).strip()

            if not content:
                return (
                    "[GÖRSEL ANALİZ HATA] "
                    f"{VISION_MODEL} boş çıktı üretti: {file_path}"
                )

            return content

        except Exception as error:
            return (
                "[GÖRSEL ANALİZ HATA] "
                f"{type(error).__name__}: {error}"
            )

    def _find_active_image_reference(self, user_request):
        active_image_path = getattr(self, "_active_image_path", None)

        if active_image_path is None:
            return None

        active_image_path = Path(active_image_path)

        if not active_image_path.exists() or not active_image_path.is_file():
            self._active_image_path = None
            return None

        request_text = str(user_request or "").strip()

        if not request_text:
            return active_image_path

        lowered = request_text.casefold()

        image_reference_keywords = (
            "görsel",
            "resim",
            "foto",
            "fotoğraf",
            "ekran görüntüsü",
            "ekrandaki",
            "resimde",
            "görselde",
            "fotoğrafta",
            "fotoda",
        )

        image_text_keywords = (
            "ne yazıyor",
            "neler yazıyor",
            "yazıları oku",
            "metinleri oku",
            "metinleri söyle",
            "yazıları söyle",
        )

        if any(keyword in lowered for keyword in image_reference_keywords):
            return active_image_path

        if any(keyword in lowered for keyword in image_text_keywords):
            return active_image_path

        return None

    def _pdf_path_from_attachment_line(self, line):
        stripped = str(line or "").strip()

        if stripped.startswith("-"):
            stripped = stripped[1:].lstrip()

        if not stripped.startswith("@"):
            return None

        raw_path = stripped[1:].strip().strip('"').strip("'")

        if not raw_path:
            return None

        raw_path = raw_path.replace("\\ ", " ")

        try:
            file_path = self._resolve_attachment_path(raw_path)
        except Exception:
            return None

        if file_path.suffix.lower() not in PDF_EXTENSIONS:
            return None

        return file_path

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

    def _prepare_user_text(self, text):
        original_text = str(text or "")

        kept_lines = []
        image_paths = []
        pdf_paths = []

        seen_image_paths = set()
        seen_pdf_paths = set()

        for line in original_text.splitlines():
            image_path = self._image_path_from_attachment_line(
                line
            )

            if image_path is not None:
                path_key = str(image_path).casefold()

                if path_key not in seen_image_paths:
                    seen_image_paths.add(path_key)
                    image_paths.append(image_path)

                continue

            pdf_path = self._pdf_path_from_attachment_line(
                line
            )

            if pdf_path is not None:
                path_key = str(pdf_path).casefold()

                if path_key not in seen_pdf_paths:
                    seen_pdf_paths.add(path_key)
                    pdf_paths.append(pdf_path)

                continue

            kept_lines.append(line)

        user_request = "\n".join(
            kept_lines
        ).strip()

        if image_paths:
            self._active_image_path = image_paths[-1]

        reused_active_image_path = None

        if not image_paths and not pdf_paths:
            reused_active_image_path = self._find_active_image_reference(
                user_request
            )

            if reused_active_image_path is None:
                return original_text

            image_paths = [reused_active_image_path]

        if not user_request:
            user_request = "Ekli dosyaları incele."

        context_sections = []

        for image_path in image_paths:
            if self._stopping:
                break

            analysis = self._analyze_image(
                image_path,
                user_request,
            )

            section_title = "GÖRSEL"

            if reused_active_image_path is not None:
                section_title = "AKTİF GÖRSEL"

            context_sections.append(
                f"----- {section_title} -----\n"
                f"Dosya: {image_path}\n"
                f"{analysis}\n"
                f"----- /{section_title} -----"
            )

        for pdf_path in pdf_paths:
            if self._stopping:
                break

            pdf_text = self._extract_pdf_text(
                pdf_path
            )

            if pdf_text:
                context_sections.append(
                    "----- PDF METNİ -----\n"
                    f"Dosya: {pdf_path}\n"
                    "Kaynak: pdftotext teknik metin çıkarımı\n"
                    f"{pdf_text}\n"
                    "----- /PDF METNİ -----"
                )
                continue

            pdf_analysis = self._analyze_pdf_visually(
                pdf_path,
                user_request,
            )

            context_sections.append(
                "----- PDF GÖRSEL ANALİZİ -----\n"
                f"Dosya: {pdf_path}\n"
                f"Kaynak model: {VISION_MODEL}\n"
                f"{pdf_analysis}\n"
                "----- /PDF GÖRSEL ANALİZİ -----"
            )

        if not context_sections:
            return user_request

        attachment_context = "\n\n".join(
            context_sections
        )

        return (
            f"{user_request}\n\n"
            "===== EKLİ DOSYA BAĞLAMI =====\n"
            "Aşağıdaki içerik ekli dosyalardan teknik olarak "
            "hazırlanmıştır.\n"
            "Metin tabanlı PDF'lerde pdftotext kullanılmıştır.\n"
            f"Taranmış/görüntü PDF veya görsellerde {VISION_MODEL} "
            "yardımcı model olarak kullanılmıştır.\n"
            "Nihai cevabı ana model olarak sen üret.\n"
            "PDF dosyaları için DOSYA_OKU aracını çağırma.\n"
            "SVG görsel analizi hata verdiyse SVG dosyasının kaynak "
            "içeriğini DOSYA_OKU ile okuyabilirsin.\n\n"
            f"{attachment_context}\n"
            "===== /EKLİ DOSYA BAĞLAMI ====="
        )
