from __future__ import annotations

import queue
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from ollama import Client
from PySide6.QtCore import QThread, Signal


OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL = "gakko-qwen38-64k-gpu:latest"
OLLAMA_CONTEXT_SIZE = 65536

VISION_MODEL = "qwen3-vl:8b"
VISION_CONTEXT_SIZE = 32768
IMAGE_EXTENSIONS = frozenset({
    ".jpeg",
    ".jpg",
    ".tif",
    ".tiff",
    ".png",
    ".svg",
    ".webp",
})
PDF_EXTENSIONS = frozenset({".pdf"})

MIN_PDF_TEXT_CHARS = 80
MAX_PDF_TEXT_CHARS = 50000
MAX_PDF_VISION_PAGES = 20
PDF_RENDER_WIDTH = 1600
PDF_RENDER_MAX_HEIGHT = 2400

PROJECT_ROOT = Path(r"D:\Gakko")
QWEN_MD_PATH = PROJECT_ROOT / ".qwen" / "QWEN.md"

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOOL_ROUNDS = 12

_STOP = object()


class QwenSession(QThread):
    ready = Signal()
    reply_ready = Signal(str)
    error_ready = Signal(str)
    context_remaining = Signal(float)

    def __init__(self, active_project_root=None):
        super().__init__()

        self.active_project_root = (
            Path(active_project_root).resolve()
            if active_project_root is not None
            else None
        )

        self._ready = False
        self._stopping = False
        self._prompt_queue = queue.Queue()
        self._messages_lock = threading.Lock()
        self._messages = []

        self.client = Client(host=OLLAMA_HOST)

        self._system_message = {
            "role": "system",
            "content": self._load_startup_context(),
        }

    @property
    def is_ready(self):
        return self._ready

    def _load_startup_context(self):
        if not QWEN_MD_PATH.exists() or not QWEN_MD_PATH.is_file():
            raise RuntimeError(f"QWEN.md bulunamadı: {QWEN_MD_PATH}")

        text = QWEN_MD_PATH.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()

        if not text:
            raise RuntimeError(f"QWEN.md boş: {QWEN_MD_PATH}")

        return (
            "Sen GAKKO'nun ana Qwen modelisin.\n"
            "Aşağıdaki QWEN.md yalnız başlangıç kapısıdır.\n"
            "Bir dosyanın içeriğine ihtiyaç duyduğunda DOSYA_OKU aracını çağır.\n"
            "Hangi dosyanın gerekli olduğuna yalnız sen karar ver.\n"
            "Python dosya, fihrist, prensip veya sonraki kaynak seçmez.\n"
            "Python yalnız senin açıkça istediğin dosyayı diskten okur ve "
            "içeriğini sana geri verir.\n\n"
            "===== QWEN.md =====\n"
            f"{text}\n"
            "===== /QWEN.md ====="
        )

    def _resolve_requested_path(self, path):
        raw = str(path or "").strip().strip('"').strip("'")
        if not raw:
            raise ValueError("Boş dosya yolu.")

        candidate = Path(raw)

        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate

        return candidate.resolve()

    def DOSYA_OKU(self, path):
        """
        Qwen'in açıkça istediği dosyanın ham metin içeriğini döndürür.

        Bu fonksiyon dosya seçmez, fihrist takip etmez, prensip eşleştirmez
        ve bir sonraki kaynağa karar vermez.
        """
        try:
            file_path = self._resolve_requested_path(path)

            if not file_path.exists():
                return f"[DOSYA_OKU HATA] Dosya bulunamadı: {file_path}"

            if not file_path.is_file():
                return f"[DOSYA_OKU HATA] Yol bir dosya değil: {file_path}"

            size = file_path.stat().st_size
            if size > MAX_FILE_BYTES:
                return (
                    "[DOSYA_OKU HATA] Dosya güvenlik sınırından büyük: "
                    f"{size} bayt > {MAX_FILE_BYTES} bayt"
                )

            raw = file_path.read_bytes()

            if b"\x00" in raw[:8192]:
                return (
                    "[DOSYA_OKU HATA] Dosya metin olarak okunamıyor: "
                    f"{file_path}"
                )

            for encoding in ("utf-8-sig", "utf-8", "cp1254"):
                try:
                    return raw.decode(encoding)
                except UnicodeDecodeError:
                    continue

            return (
                "[DOSYA_OKU HATA] Dosya metin olarak çözümlenemedi: "
                f"{file_path}"
            )

        except Exception as error:
            return f"[DOSYA_OKU HATA] {type(error).__name__}: {error}"

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
            file_path = self._resolve_requested_path(raw_path)
        except Exception:
            return None

        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            return None

        return file_path

    def _analyze_image(self, file_path, user_request):
        try:
            if not file_path.exists():
                return f"[GÖRSEL ANALİZ HATA] Dosya bulunamadı: {file_path}"

            if not file_path.is_file():
                return f"[GÖRSEL ANALİZ HATA] Yol bir dosya değil: {file_path}"

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

            response = self.client.chat(
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
            file_path = self._resolve_requested_path(raw_path)
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
                "[PDF METİN] pdftotext bulunamadı; görsel yola geçiliyor.",
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
                            round(render_width * scale),
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

    def _analyze_pdf_visually(self, file_path, user_request):
        try:
            if not file_path.exists():
                return f"[PDF ANALİZ HATA] Dosya bulunamadı: {file_path}"

            if not file_path.is_file():
                return f"[PDF ANALİZ HATA] Yol bir dosya değil: {file_path}"

            if self._stopping:
                return "[PDF ANALİZ DURDU]"

            with tempfile.TemporaryDirectory(
                prefix="gakko-pdf-vision-"
            ) as temp_dir:
                image_paths, page_count = self._render_pdf_pages(
                    file_path,
                    Path(temp_dir),
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

                response = self.client.chat(
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
                    options={"num_ctx": VISION_CONTEXT_SIZE},
                )

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
            image_path = self._image_path_from_attachment_line(line)

            if image_path is not None:
                path_key = str(image_path).casefold()

                if path_key not in seen_image_paths:
                    seen_image_paths.add(path_key)
                    image_paths.append(image_path)

                continue

            pdf_path = self._pdf_path_from_attachment_line(line)

            if pdf_path is not None:
                path_key = str(pdf_path).casefold()

                if path_key not in seen_pdf_paths:
                    seen_pdf_paths.add(path_key)
                    pdf_paths.append(pdf_path)

                continue

            kept_lines.append(line)

        if not image_paths and not pdf_paths:
            return original_text

        user_request = "\n".join(kept_lines).strip()
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

            context_sections.append(
                "----- GÖRSEL -----\n"
                f"Dosya: {image_path}\n"
                f"{analysis}\n"
                "----- /GÖRSEL -----"
            )

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

    def _tool_definition(self):
        return {
            "type": "function",
            "function": {
                "name": "DOSYA_OKU",
                "description": (
                    "İhtiyaç duyduğun metin dosyasını oku. "
                    "Hangi dosyanın gerekli olduğuna yalnız sen karar verirsin. "
                    "Python dosya, fihrist veya prensip seçmez."
                ),
                "parameters": {
                    "type": "object",
                    "required": ["path"],
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Okunacak dosyanın tam yolu veya "
                                "D:\\Gakko köküne göre göreli yolu."
                            ),
                        }
                    },
                },
            },
        }

    def submit_prompt(self, text):
        text = str(text or "").strip()

        if not text:
            self.error_ready.emit("Boş mesaj gönderilemez.")
            return False

        if not self._ready:
            self.error_ready.emit("Qwen henüz hazır değil.")
            return False

        self._prompt_queue.put(text)
        return True

    def reset_context(self):
        if not self._ready:
            self.error_ready.emit("Qwen henüz hazır değil.")
            return False

        with self._messages_lock:
            self._messages.clear()

        self.context_remaining.emit(100.0)
        return True

    def _messages_for_prompt(self, text):
        with self._messages_lock:
            return [
                self._system_message,
                *self._messages,
                {"role": "user", "content": text},
            ]

    def _remember_exchange(self, user_text, assistant_text):
        with self._messages_lock:
            self._messages.append(
                {"role": "user", "content": user_text}
            )
            self._messages.append(
                {"role": "assistant", "content": assistant_text}
            )

    def _emit_context_remaining(self, response):
        try:
            prompt_tokens = int(
                getattr(response, "prompt_eval_count", 0) or 0
            )
            eval_tokens = int(
                getattr(response, "eval_count", 0) or 0
            )

            used = max(0, prompt_tokens + eval_tokens)
            used = min(used, OLLAMA_CONTEXT_SIZE)

            remaining = 100.0 * (
                1.0 - (used / OLLAMA_CONTEXT_SIZE)
            )

            self.context_remaining.emit(
                max(0.0, min(100.0, remaining))
            )

        except Exception:
            return

    def _create_measurement_totals(self):
        return {
            "total_duration": 0,
            "load_duration": 0,
            "prompt_eval_count": 0,
            "prompt_eval_duration": 0,
            "eval_count": 0,
            "eval_duration": 0,
        }

    def _add_response_measurement(self, totals, response):
        for metric_name in totals:
            try:
                value = getattr(response, metric_name, 0) or 0
                totals[metric_name] += int(value)
            except (TypeError, ValueError):
                continue

    def _print_measurement(self, started_at, totals, rounds):
        elapsed_seconds = time.perf_counter() - started_at

        model_seconds = (
            totals["total_duration"] / 1_000_000_000
        )
        load_seconds = (
            totals["load_duration"] / 1_000_000_000
        )
        prompt_seconds = (
            totals["prompt_eval_duration"] / 1_000_000_000
        )
        eval_seconds = (
            totals["eval_duration"] / 1_000_000_000
        )

        prompt_tokens = totals["prompt_eval_count"]
        eval_tokens = totals["eval_count"]

        if eval_seconds > 0:
            tokens_per_second = eval_tokens / eval_seconds
        else:
            tokens_per_second = 0.0

        print(
            "[QWEN ÖLÇÜM] "
            f"toplam={elapsed_seconds:.2f} sn | "
            f"model={model_seconds:.2f} sn | "
            f"yükleme={load_seconds:.2f} sn | "
            f"giriş={prompt_seconds:.2f} sn / "
            f"{prompt_tokens} tok | "
            f"üretim={eval_seconds:.2f} sn / "
            f"{eval_tokens} tok / "
            f"{tokens_per_second:.1f} tok/sn | "
            f"tur={rounds}",
            flush=True,
        )

    def _chat_with_tools(self, user_text):
        messages = self._messages_for_prompt(user_text)
        tool = self._tool_definition()
        last_response = None

        started_at = time.perf_counter()
        rounds = 0
        totals = self._create_measurement_totals()

        for _ in range(MAX_TOOL_ROUNDS):
            if self._stopping:
                return None

            response = self.client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=[tool],
                stream=False,
                options={"num_ctx": OLLAMA_CONTEXT_SIZE},
            )

            last_response = response
            rounds += 1

            self._add_response_measurement(
                totals,
                response,
            )

            assistant_message = response.message
            messages.append(assistant_message)

            tool_calls = assistant_message.tool_calls or []

            if not tool_calls:
                self._emit_context_remaining(response)

                self._print_measurement(
                    started_at,
                    totals,
                    rounds,
                )

                return (
                    assistant_message.content or ""
                ).strip()

            for tool_call in tool_calls:
                if self._stopping:
                    return None

                tool_name = tool_call.function.name
                arguments = (
                    tool_call.function.arguments or {}
                )

                if tool_name != "DOSYA_OKU":
                    result = (
                        "[TOOL HATA] Bilinmeyen araç: "
                        f"{tool_name}"
                    )
                else:
                    requested_path = str(
                        arguments.get("path", "")
                    )

                    print(
                        f"[QWEN DOSYA İSTEDİ] "
                        f"{requested_path}"
                    )

                    result = self.DOSYA_OKU(
                        requested_path
                    )

                messages.append(
                    {
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": result,
                    }
                )

        if last_response is not None:
            self._emit_context_remaining(
                last_response
            )

        self._print_measurement(
            started_at,
            totals,
            rounds,
        )

        raise RuntimeError(
            f"Qwen {MAX_TOOL_ROUNDS} araç turu içinde "
            "nihai cevap üretmedi."
        )

    def run(self):
        self._ready = True
        self.context_remaining.emit(100.0)
        self.ready.emit()

        try:
            while not self._stopping:
                try:
                    item = self._prompt_queue.get(
                        timeout=0.1
                    )
                except queue.Empty:
                    continue

                if item is _STOP:
                    break

                user_text = str(item)
                prepared_user_text = self._prepare_user_text(
                    user_text
                )

                try:
                    reply = self._chat_with_tools(
                        prepared_user_text
                    )
                except Exception as error:
                    if not self._stopping:
                        self.error_ready.emit(
                            str(error)
                        )
                    continue

                if self._stopping or reply is None:
                    break

                self._remember_exchange(
                    prepared_user_text,
                    reply,
                )

                self.reply_ready.emit(reply)

        finally:
            self._ready = False

    def stop(self):
        self._stopping = True
        self._ready = False
        self._prompt_queue.put(_STOP)