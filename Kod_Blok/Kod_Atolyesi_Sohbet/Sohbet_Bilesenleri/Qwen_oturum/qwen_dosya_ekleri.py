from __future__ import annotations

from pathlib import Path

from .Dosya_ekleri.pdf_ayarlari import PdfAyarlariMixin
from .qwen_ayarlar import (
    IMAGE_EXTENSIONS,
    VISION_CONTEXT_SIZE,
    VISION_MODEL,
    _CANCELLED,
)


class QwenDosyaEkleriMixin(PdfAyarlariMixin):
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

    def _attachment_path_from_line(self, line, extensions):
        stripped = str(line or "").strip()

        if stripped.startswith("-"):
            stripped = stripped[1:].lstrip()

        if not stripped.startswith("@"):
            return None

        raw_path = stripped[1:].strip().strip('"').strip("'")
        if not raw_path:
            return None

        try:
            file_path = self._resolve_attachment_path(raw_path.replace("\\ ", " "))
        except Exception:
            return None

        return file_path if file_path.suffix.lower() in extensions else None

    def _image_path_from_attachment_line(self, line):
        return self._attachment_path_from_line(line, IMAGE_EXTENSIONS)
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
            "görsel", "resim", "foto", "fotoğraf", "ekran görüntüsü",
            "ekrandaki", "resimde", "görselde", "fotoğrafta", "fotoda",
            "ne yazıyor", "neler yazıyor", "yazıları oku", "metinleri oku",
            "metinleri söyle", "yazıları söyle",
        )

        if any(keyword in lowered for keyword in image_reference_keywords):
            return active_image_path

        return None


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
            "SVG görsel analizi hata verdiyse SVG kaynak içeriğini "
            "read_text_file ile okuyabilirsin.\n\n"
            f"{attachment_context}\n"
            "===== /EKLİ DOSYA BAĞLAMI ====="
        )
