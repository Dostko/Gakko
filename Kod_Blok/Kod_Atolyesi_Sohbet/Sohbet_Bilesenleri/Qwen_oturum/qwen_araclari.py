from __future__ import annotations

import json
import ntpath
import re
import uuid
from pathlib import Path
from urllib.parse import quote

from ..internet_giris import (
    INTERNET_TOOL_NAMES,
    internet_araci_calistir,
)
from ..git_kayitlari import call_git_tool, guard_git_commit_claim
from .ai_arac_cagrisi import (
    KODCU_AI_TOOL,
    KODCU_AI_TOOL_NAME,
    kod_gorevi_mi,
    kodcu_ai_calistir,
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
DIRECTORY_TREE_TOOL_NAME = "directory_tree"
DIRECTORY_TREE_REQUEST_TERMS = (
    "directory_tree",
    "directory tree",
    "dizin ağacı",
    "dizin agaci",
    "klasör ağacı",
    "klasor agaci",
    "proje ağacı",
    "proje agaci",
    "dosya ağacı",
    "dosya agaci",
)
WEB_USAGE_LIMIT_MESSAGE = (
    "[INTERNET KULLANIM SINIRI] "
    "web_search/web_fetch sınırı doldu. Yeni internet araması yapma; "
    "mevcut kaynaklarla nihai cevabı üret."
)
GIT_COMMIT_VERIFIED_MARKER = "[GIT COMMIT DOĞRULANDI]"


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

    def _has_visual_attachment_context(self, user_text):
        text = str(user_text or "")

        if "===== EKLİ DOSYA BAĞLAMI =====" not in text:
            return False

        return any(
            marker in text
            for marker in (
                "----- GÖRSEL -----",
                "----- AKTİF GÖRSEL -----",
            )
        )

    def _tools_for_prompt(self, user_text, runtime):
        text = str(user_text or "").casefold()
        tools = list(runtime.tools)
        model_mode = str(getattr(self, "_model_mode", "auto") or "auto")

        if (
            model_mode == "auto"
            and self._has_visual_attachment_context(user_text)
        ):
            tools.append(KODCU_AI_TOOL)

        if any(term in text for term in DIRECTORY_TREE_REQUEST_TERMS):
            return tools

        return [
            tool
            for tool in tools
            if str(tool.get("function", {}).get("name", ""))
            != DIRECTORY_TREE_TOOL_NAME
        ]

    def _prepare_coder_context(self, user_text):
        model_mode = str(getattr(self, "_model_mode", "auto") or "auto")

        if model_mode == "normal":
            return user_text

        if model_mode == "auto":
            if self._has_visual_attachment_context(user_text):
                return user_text

            if not kod_gorevi_mi(user_text):
                return user_text

        activity = {"name": "kodcu_ai"}
        self.tool_activity.emit(json.dumps(activity, ensure_ascii=False))
        print(
            (
                "[GAKKO KODCU] Kod modu seçildi; Kodcu çağrılıyor."
                if model_mode == "kod"
                else "[GAKKO KODCU] Kod görevi algılandı; Kodcu çağrılıyor."
            ),
            flush=True,
        )

        result = kodcu_ai_calistir(self, user_text)
        if result is _CANCELLED:
            return _CANCELLED

        return (
            f"{user_text}\n\n"
            "===== KODCU UZMAN BAĞLAMI =====\n"
            f"{result}\n"
            "===== /KODCU UZMAN BAĞLAMI =====\n"
            "Yukarıdaki uzman çıktısını teknik bağlam olarak kullan. "
            "Nihai cevabı GAKKO'nun ana modeli olarak sen üret."
        )

    async def _execute_qwen_tool(self, runtime, name, arguments):
        if name == KODCU_AI_TOOL_NAME:
            gorev = (
                arguments.get("gorev")
                if isinstance(arguments, dict)
                else ""
            )
            return kodcu_ai_calistir(self, gorev)

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

        if name in runtime.git_tool_names:
            return await call_git_tool(self, runtime, name, arguments)

        if name in INTERNET_TOOL_NAMES:
            return internet_araci_calistir(name, arguments)

        return f"[TOOL HATA] Bilinmeyen araç: {name}"

    async def _chat_with_tools(self, user_text, runtime):
        prepared_text = self._prepare_coder_context(user_text)
        if prepared_text is _CANCELLED:
            return _CANCELLED

        messages = self._messages_for_prompt(prepared_text)
        tools = self._tools_for_prompt(prepared_text, runtime)
        self._generated_image_paths = {}

        last_response = None
        web_research_tool_calls = 0
        git_commit_verified = False

        for _ in range(MAX_TOOL_ROUNDS):
            if self._stopping:
                return None

            if self._cancel_requested.is_set():
                return _CANCELLED

            try:
                response = self._chat(
                    model=OLLAMA_MODEL,
                    messages=messages,
                    tools=tools,
                    stream=False,
                    think=True,
                    options={"num_ctx": OLLAMA_CONTEXT_SIZE},
                )

            except Exception as exc:
                print(
                    f"[QWEN HATA] {type(exc).__name__}: {exc}",
                    flush=True,
                )
                raise

            if response is _CANCELLED:
                return _CANCELLED

            last_response = response
            assistant_message = response.message
            messages.append(assistant_message)

            tool_calls = assistant_message.tool_calls or []

            if not tool_calls:
                self._emit_context_remaining(response)
                final_text = str(assistant_message.content or "").strip()
                final_text = self._rewrite_generated_image_references(
                    final_text
                )
                return guard_git_commit_claim(
                    final_text,
                    git_commit_verified,
                )

            for tool_call in tool_calls:
                if self._stopping or self._cancel_requested.is_set():
                    return _CANCELLED

                name = str(tool_call.function.name or "").strip()
                arguments = tool_call.function.arguments or {}

                if not name:
                    raise RuntimeError("Qwen araç çağrısında araç adı yok.")

                arguments = self._prepare_mcp_arguments(name, arguments)

                activity = {"name": name}
                for key in ("path", "repo_path", "query", "pattern", "url"):
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

                    if result is _CANCELLED:
                        return _CANCELLED

                    if (
                        name == "git_commit"
                        and GIT_COMMIT_VERIFIED_MARKER in str(result)
                    ):
                        git_commit_verified = True

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
