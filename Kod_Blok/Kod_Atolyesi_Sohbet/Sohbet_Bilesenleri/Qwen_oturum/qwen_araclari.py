from __future__ import annotations

import json
import ntpath
import re
import time
import uuid
from pathlib import Path
from urllib.parse import quote

from ..internet_giris import (
    INTERNET_TOOL_NAMES,
    internet_araci_calistir,
)
from .qwen_ayarlar import (
    IMAGE_EXTENSIONS,
    MAX_TOOL_ROUNDS,
    MAX_WEB_TOOL_CALLS,
    OLLAMA_CONTEXT_SIZE,
    OLLAMA_MODEL,
    PROJECT_ROOT,
    _CANCELLED,
)


GENERATED_IMAGE_EXTENSIONS = IMAGE_EXTENSIONS | frozenset({
    ".bmp",
    ".gif",
    ".ico",
})
GENERATED_IMAGE_TARGET_ROOT = PROJECT_ROOT / "Gorseller"

WEB_RESEARCH_TOOL_NAMES = frozenset({"web_search", "web_fetch"})
WEB_USAGE_LIMIT_MESSAGE = (
    "[INTERNET KULLANIM SINIRI] "
    "web_search/web_fetch sınırı doldu. Yeni internet araması yapma; "
    "mevcut kaynaklarla nihai cevabı üret."
)


class QwenAraclariMixin:
    def _prepare_mcp_arguments(self, name, arguments):
        if not isinstance(arguments, dict):
            return arguments

        generated_paths = getattr(self, "_generated_image_paths", {})

        def redirected(value):
            raw_value = str(value or "").strip()
            if not raw_value:
                return value
            key = ntpath.normcase(ntpath.normpath(raw_value))
            mapped = generated_paths.get(key)
            return mapped[1] if mapped is not None else value

        for key in ("path", "source", "destination"):
            if key in arguments:
                arguments[key] = redirected(arguments[key])

        paths = arguments.get("paths")
        if isinstance(paths, list):
            arguments["paths"] = [redirected(path) for path in paths]

        raw_path = str(arguments.get("path") or "").strip()
        if not raw_path:
            return arguments

        normalized_path = ntpath.normcase(ntpath.normpath(raw_path))
        redirected_path = generated_paths.get(normalized_path)

        if redirected_path is not None:
            arguments["path"] = redirected_path[1]
            return arguments

        if name != "write_file":
            return arguments

        suffix = ntpath.splitext(normalized_path)[1].lower()
        if suffix not in GENERATED_IMAGE_EXTENSIONS:
            return arguments

        target_root = ntpath.normcase(
            ntpath.normpath(str(GENERATED_IMAGE_TARGET_ROOT))
        )
        try:
            is_generated_image = (
                ntpath.commonpath([normalized_path, target_root])
                == target_root
            )
        except ValueError:
            is_generated_image = False

        generated_images_root = getattr(
            self,
            "generated_images_root",
            None,
        )
        if not is_generated_image or generated_images_root is None:
            return arguments

        temp_root = Path(generated_images_root)
        temp_root.mkdir(parents=True, exist_ok=True)
        source_name = ntpath.basename(raw_path)
        source_stem = ntpath.splitext(source_name)[0] or "gakko_gorseli"
        temp_path = temp_root / (
            f"{source_stem}_{uuid.uuid4().hex[:8]}{suffix}"
        )

        redirected_path = (raw_path, str(temp_path))
        generated_paths[normalized_path] = redirected_path
        self._generated_image_paths = generated_paths
        arguments["path"] = redirected_path[1]
        return arguments

    def _rewrite_generated_image_references(self, text):
        rewritten = str(text or "")

        for original_path, temp_path in getattr(
            self,
            "_generated_image_paths",
            {},
        ).values():
            original_forward = original_path.replace("\\", "/")
            temp_forward = temp_path.replace("\\", "/")
            original_uri = f"file:///{original_forward.lstrip('/')}"
            encoded_original_uri = "file:///" + quote(
                original_forward.lstrip("/"),
                safe="/:",
            )
            temp_uri = f"file:///{temp_forward.lstrip('/')}"

            replacements = (
                (encoded_original_uri, temp_uri),
                (original_uri, temp_uri),
                (original_forward, temp_forward),
                (original_path, temp_path),
            )
            for old_value, new_value in replacements:
                rewritten = re.sub(
                    re.escape(old_value),
                    lambda _match, value=new_value: value,
                    rewritten,
                    flags=re.IGNORECASE,
                )

        return rewritten

    def _emit_context_remaining(self, response):
        try:
            used = int(getattr(response, "prompt_eval_count", 0) or 0)
            used += int(getattr(response, "eval_count", 0) or 0)
            used = min(max(used, 0), OLLAMA_CONTEXT_SIZE)
            remaining = 100.0 * (1.0 - (used / OLLAMA_CONTEXT_SIZE))
            self.context_remaining.emit(min(max(remaining, 0.0), 100.0))
        except Exception:
            pass

    async def _execute_qwen_tool(self, runtime, name, arguments):
        if name in runtime.search_tool_names:
            return await self._call_mcp_tool(
                runtime.search_client,
                name,
                arguments,
            )

        if name in runtime.tool_names:
            return await self._call_mcp_tool(
                runtime.client,
                name,
                arguments,
            )

        if name in INTERNET_TOOL_NAMES:
            return internet_araci_calistir(name, arguments)

        return f"[TOOL HATA] Bilinmeyen araç: {name}"

    async def _chat_with_tools(self, user_text, runtime):
        messages = self._messages_for_prompt(user_text)
        self._generated_image_paths = {}

        last_response = None
        rounds = 0
        web_research_tool_calls = 0

        for _ in range(MAX_TOOL_ROUNDS):
            if self._stopping:
                return None

            if self._cancel_requested.is_set():
                return _CANCELLED

            model_started_at = time.perf_counter()
            print(
                f"[QWEN YANITI BEKLENİYOR] Tur: {rounds + 1}",
                flush=True,
            )
            try:
                response = self._chat(
                    model=OLLAMA_MODEL,
                    messages=messages,
                    tools=runtime.tools,
                    stream=False,
                    options={"num_ctx": OLLAMA_CONTEXT_SIZE},
                )
            except Exception as exc:
                print(
                    f"[QWEN HATA] Tur: {rounds + 1} | "
                    f"Süre: {time.perf_counter() - model_started_at:.2f} sn | "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
                raise

            print(
                f"[{'QWEN İPTAL EDİLDİ' if response is _CANCELLED else 'QWEN YANITI GELDİ'}] "
                f"Tur: {rounds + 1} | "
                f"Süre: {time.perf_counter() - model_started_at:.2f} sn",
                flush=True,
            )

            if response is _CANCELLED:
                return _CANCELLED

            last_response = response
            rounds += 1
            assistant_message = response.message
            messages.append(assistant_message)

            tool_calls = assistant_message.tool_calls or []

            if not tool_calls:
                self._emit_context_remaining(response)
                final_text = str(assistant_message.content or "").strip()
                final_text = self._rewrite_generated_image_references(
                    final_text
                )
                return final_text

            for tool_call in tool_calls:
                if self._stopping or self._cancel_requested.is_set():
                    return _CANCELLED

                name = str(tool_call.function.name or "").strip()
                arguments = tool_call.function.arguments or {}

                if not name:
                    raise RuntimeError("Qwen araç çağrısında araç adı yok.")

                arguments = self._prepare_mcp_arguments(name, arguments)

                activity = {"name": name}
                for key in ("path", "query", "pattern", "url"):
                    value = arguments.get(key)
                    if value not in (None, ""):
                        activity[key] = str(value)[:240]
                self.tool_activity.emit(json.dumps(activity, ensure_ascii=False))

                is_web_research_tool = name in WEB_RESEARCH_TOOL_NAMES

                if (
                    is_web_research_tool
                    and web_research_tool_calls >= MAX_WEB_TOOL_CALLS
                ):
                    result = WEB_USAGE_LIMIT_MESSAGE
                    print(
                        "[QWEN INTERNET] "
                        f"kullanım={web_research_tool_calls}/{MAX_WEB_TOOL_CALLS} | "
                        f"{name} çalıştırılmadı.",
                        flush=True,
                    )
                else:
                    result = await self._execute_qwen_tool(
                        runtime,
                        name,
                        arguments,
                    )

                    if is_web_research_tool:
                        web_research_tool_calls += 1
                        print(
                            "[QWEN INTERNET] "
                            f"kullanım={web_research_tool_calls}/{MAX_WEB_TOOL_CALLS}",
                            flush=True,
                        )
                        if (
                            web_research_tool_calls
                            >= MAX_WEB_TOOL_CALLS
                        ):
                            result = (
                                f"{result}\n\n{WEB_USAGE_LIMIT_MESSAGE}"
                            )

                messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": result,
                    }
                )

        if last_response is not None:
            self._emit_context_remaining(last_response)

        raise RuntimeError(
            f"Qwen {MAX_TOOL_ROUNDS} araç turu içinde nihai cevap üretmedi."
        )
