from __future__ import annotations

import queue
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
    ".png",
    ".webp",
})

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

    def _prepare_user_text(self, text):
        original_text = str(text or "")
        kept_lines = []
        image_paths = []
        seen_paths = set()

        for line in original_text.splitlines():
            image_path = self._image_path_from_attachment_line(line)

            if image_path is None:
                kept_lines.append(line)
                continue

            path_key = str(image_path).casefold()

            if path_key not in seen_paths:
                seen_paths.add(path_key)
                image_paths.append(image_path)

        if not image_paths:
            return original_text

        user_request = "\n".join(kept_lines).strip()
        if not user_request:
            user_request = "Ekli görseli incele."

        vision_sections = []

        for image_path in image_paths:
            if self._stopping:
                break

            analysis = self._analyze_image(
                image_path,
                user_request,
            )

            vision_sections.append(
                "----- GÖRSEL -----\n"
                f"Dosya: {image_path}\n"
                f"{analysis}\n"
                "----- /GÖRSEL -----"
            )

        if not vision_sections:
            return user_request

        vision_context = "\n\n".join(vision_sections)

        return (
            f"{user_request}\n\n"
            "===== YARDIMCI GÖRSEL MODEL BAĞLAMI =====\n"
            f"Kaynak model: {VISION_MODEL}\n"
            "Aşağıdaki görsel içeriği yardımcı model tarafından okunmuştur.\n"
            "Nihai cevabı ana model olarak sen üret.\n"
            "Bu görseller için DOSYA_OKU aracını çağırma.\n\n"
            f"{vision_context}\n"
            "===== /YARDIMCI GÖRSEL MODEL BAĞLAMI ====="
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