from __future__ import annotations

import time

from ..internet_giris import (
    INTERNET_TOOL_NAMES,
    INTERNET_TOOLS,
    internet_araci_calistir,
)

from .qwen_ayarlar import (
    MAX_TOOL_ROUNDS,
    OLLAMA_CONTEXT_SIZE,
    OLLAMA_MODEL,
    _CANCELLED,
)


class QwenAraclariMixin:
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

    def _directory_tool_definition(self):
        return {
            "type": "function",
            "function": {
                "name": "list_project_directory",
                "description": (
                    "Aktif proje kökü içindeki bir klasörün gerçek dosya ve "
                    "klasör adlarını listeler. Proje yapısını görmek gerektiğinde "
                    "dosya adı tahmin etmek yerine bu aracı kullan."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": (
                                "Aktif proje köküne göre listelenecek klasör yolu. "
                                "Proje kökü için boş bırak."
                            ),
                            "default": "",
                        },
                    },
                },
            },
        }

    def _write_tool_definition(self):
        return {
            "type": "function",
            "function": {
                "name": "DOSYA_YAZ",
                "description": (
                    "Kullanıcının isteği veya onayı kapsamındaki metin "
                    "dosyasını aktif proje kökü içinde oluştur veya değiştir. "
                    "Dosya yolu ve içeriğine yalnız sen karar verirsin. "
                    "Python yalnız teknik yazma işlemini uygular."
                ),
                "parameters": {
                    "type": "object",
                    "required": ["path", "content"],
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Yazılacak dosyanın tam yolu veya aktif "
                                "proje köküne göre göreli yolu."
                            ),
                        },
                        "content": {
                            "type": "string",
                            "description": (
                                "Dosyaya UTF-8 olarak yazılacak tam metin."
                            ),
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": (
                                "Mevcut dosyanın üzerine yazılacaksa true. "
                                "Varsayılan false."
                            ),
                            "default": False,
                        },
                    },
                },
            },
        }

    def _emit_context_remaining(self, response):
        try:
            prompt_tokens = int(
                getattr(response, "prompt_eval_count", 0) or 0
            )

            eval_tokens = int(
                getattr(response, "eval_count", 0) or 0
            )

            used = max(
                0,
                prompt_tokens + eval_tokens,
            )

            used = min(
                used,
                OLLAMA_CONTEXT_SIZE,
            )

            remaining = 100.0 * (
                1.0
                - (
                    used
                    / OLLAMA_CONTEXT_SIZE
                )
            )

            self.context_remaining.emit(
                max(
                    0.0,
                    min(
                        100.0,
                        remaining,
                    ),
                )
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

    def _add_response_measurement(
        self,
        totals,
        response,
    ):
        for metric_name in totals:
            try:
                value = (
                    getattr(
                        response,
                        metric_name,
                        0,
                    )
                    or 0
                )

                totals[metric_name] += int(value)

            except (TypeError, ValueError):
                continue

    def _print_measurement(
        self,
        started_at,
        totals,
        rounds,
    ):
        elapsed_seconds = (
            time.perf_counter()
            - started_at
        )

        model_seconds = (
            totals["total_duration"]
            / 1_000_000_000
        )

        load_seconds = (
            totals["load_duration"]
            / 1_000_000_000
        )

        prompt_seconds = (
            totals["prompt_eval_duration"]
            / 1_000_000_000
        )

        eval_seconds = (
            totals["eval_duration"]
            / 1_000_000_000
        )

        prompt_tokens = totals[
            "prompt_eval_count"
        ]

        eval_tokens = totals[
            "eval_count"
        ]

        if eval_seconds > 0:
            tokens_per_second = (
                eval_tokens
                / eval_seconds
            )
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
        messages = self._messages_for_prompt(
            user_text
        )

        read_tool = self._tool_definition()

        directory_tool = (
            self._directory_tool_definition()
        )

        write_tool = (
            self._write_tool_definition()
        )

        tools = [
            read_tool,
            directory_tool,
            write_tool,
            *INTERNET_TOOLS,
        ]

        last_response = None

        started_at = time.perf_counter()
        rounds = 0

        totals = (
            self._create_measurement_totals()
        )

        for _ in range(MAX_TOOL_ROUNDS):
            if self._stopping:
                return None

            if self._cancel_requested.is_set():
                return _CANCELLED

            response = self._chat(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=tools,
                stream=False,
                options={
                    "num_ctx": OLLAMA_CONTEXT_SIZE
                },
            )

            if response is _CANCELLED:
                return _CANCELLED

            last_response = response
            rounds += 1

            self._add_response_measurement(
                totals,
                response,
            )

            assistant_message = (
                response.message
            )

            messages.append(
                assistant_message
            )

            tool_calls = (
                assistant_message.tool_calls
                or []
            )

            if not tool_calls:
                self._emit_context_remaining(
                    response
                )

                self._print_measurement(
                    started_at,
                    totals,
                    rounds,
                )

                return (
                    assistant_message.content
                    or ""
                ).strip()

            for tool_call in tool_calls:
                if self._stopping:
                    return None

                if self._cancel_requested.is_set():
                    return _CANCELLED

                tool_name = (
                    tool_call.function.name
                )

                arguments = (
                    tool_call.function.arguments
                    or {}
                )

                if tool_name == "DOSYA_OKU":
                    requested_path = str(
                        arguments.get(
                            "path",
                            "",
                        )
                    )

                    print(
                        "[QWEN DOSYA İSTEDİ] "
                        f"{requested_path}"
                    )

                    result = self.DOSYA_OKU(
                        requested_path
                    )

                elif (
                    tool_name
                    == "list_project_directory"
                ):
                    relative_path = str(
                        arguments.get(
                            "relative_path",
                            "",
                        )
                    )

                    print(
                        "[QWEN KLASÖR İSTEDİ] "
                        f"{relative_path or '.'}"
                    )

                    result = (
                        self.list_project_directory(
                            relative_path
                        )
                    )

                elif tool_name == "DOSYA_YAZ":
                    result = self.DOSYA_YAZ(
                        arguments.get(
                            "path",
                            "",
                        ),
                        arguments.get(
                            "content",
                            "",
                        ),
                        arguments.get(
                            "overwrite",
                            False,
                        ),
                    )

                elif (
                    tool_name
                    in INTERNET_TOOL_NAMES
                ):
                    result = (
                        internet_araci_calistir(
                            tool_name,
                            arguments,
                        )
                    )

                else:
                    result = (
                        "[TOOL HATA] "
                        "Bilinmeyen araç: "
                        f"{tool_name}"
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
            f"Qwen {MAX_TOOL_ROUNDS} araç turu "
            "içinde nihai cevap üretmedi."
        )