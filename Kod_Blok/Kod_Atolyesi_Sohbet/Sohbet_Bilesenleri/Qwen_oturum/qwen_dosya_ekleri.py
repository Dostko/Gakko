from __future__ import annotations

from pathlib import Path

from .Dosya_ekleri.pdf_ayarlari import PdfAyarlariMixin


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
            file_path = self._resolve_attachment_path(
                raw_path.replace("\\ ", " ")
            )
        except Exception:
            return None

        return (
            file_path
            if file_path.suffix.lower() in extensions
            else None
        )

    def _prepare_user_text(self, text):
        original_text = str(text or "")

        kept_lines = []
        pdf_paths = []
        seen_pdf_paths = set()

        for line in original_text.splitlines():
            pdf_path = self._pdf_path_from_attachment_line(line)

            if pdf_path is not None:
                path_key = str(pdf_path).casefold()

                if path_key not in seen_pdf_paths:
                    seen_pdf_paths.add(path_key)
                    pdf_paths.append(pdf_path)

                continue

            kept_lines.append(line)

        if not pdf_paths:
            return original_text

        user_request = "\n".join(kept_lines).strip()

        if not user_request:
            user_request = "Ekli PDF dosyasını incele."

        context_sections = []

        for pdf_path in pdf_paths:
            if self._stopping:
                break

            pdf_text = self._extract_pdf_text(pdf_path)

            if pdf_text:
                context_sections.append(
                    "----- PDF METNİ -----\n"
                    f"Dosya: {pdf_path}\n"
                    "Kaynak: pdftotext teknik metin çıkarımı\n"
                    f"{pdf_text}\n"
                    "----- /PDF METNİ -----"
                )
            else:
                context_sections.append(
                    "----- PDF METİN ÇIKARIMI -----\n"
                    f"Dosya: {pdf_path}\n"
                    "PDF dosyasından metin çıkarılamadı.\n"
                    "----- /PDF METİN ÇIKARIMI -----"
                )

        if not context_sections:
            return user_request

        attachment_context = "\n\n".join(context_sections)

        return (
            f"{user_request}\n\n"
            "===== EKLİ DOSYA BAĞLAMI =====\n"
            "Aşağıdaki içerik ekli PDF dosyalarından teknik olarak "
            "hazırlanmıştır.\n"
            "Metin tabanlı PDF'lerde pdftotext kullanılmıştır.\n\n"
            f"{attachment_context}\n"
            "===== /EKLİ DOSYA BAĞLAMI ====="
        )
