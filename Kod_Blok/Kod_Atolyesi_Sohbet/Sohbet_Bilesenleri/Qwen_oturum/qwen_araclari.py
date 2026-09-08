from __future__ import annotations

import asyncio
import json
import os
import time

from mcp import Client as MCPClient, StdioServerParameters

from ..internet_giris import (
    INTERNET_TOOL_NAMES,
    INTERNET_TOOLS,
    internet_araci_calistir,
)

from .qwen_ayarlar import (
    MAX_TOOL_ROUNDS,
    OLLAMA_CONTEXT_SIZE,
    OLLAMA_MODEL,
    PROJECT_ROOT,
    _CANCELLED,
)


NODE_DIR = r"C:\Program Files\nodejs"


def _mcp_tool_to_ollama(tool):
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)

    if hasattr(schema, "model_dump"):
        schema = schema.model_dump(by_alias=True)

    if not isinstance(schema, dict):
        schema = {
            "type": "object",
            "properties": {},
        }

    return {
        "type": "function",
        "function": {
            "name": str(tool.name),
            "description": str(
                getattr(tool, "description", "") or ""
            ),
            "parameters": schema,
        },
    }


def _mcp_result_to_text(result):
    parts = []

    for block in list(getattr(result, "content", None) or []):
        text = getattr(block, "text", None)
        if isinstance(text, str) and text:
            parts.append(text)
            continue

        if hasattr(block, "model_dump"):
            payload = block.model_dump(
                mode="json",
                by_alias=True,
            )
            parts.append(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                )
            )

    structured = getattr(
        result,
        "structured_content",
        None,
    )

    if structured is not None and not parts:
        parts.append(
            json.dumps(
                structured,
                ensure_ascii=False,
            )
        )

    text = "\n".join(parts).strip()

    if not text:
        text = "[MCP] Araç boş sonuç döndürdü."

    if bool(getattr(result, "is_error", False)):
        return f"[MCP HATA] {text}"

    return text


class QwenAraclariMixin:

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

    def _filesystem_server_parameters(self):
        allowed_directories = [
            str(
                (
                    PROJECT_ROOT
                    / "GAKKO_YUVA"
                ).resolve()
            )
        ]

        if self.active_project_root is not None:
            active_project = str(
                self.active_project_root.resolve()
            )

            if active_project not in allowed_directories:
                allowed_directories.append(
                    active_project
                )

        path_value = os.environ.get(
            "PATH",
            "",
        )

        if NODE_DIR.casefold() not in path_value.casefold():
            path_value = (
                NODE_DIR
                + os.pathsep
                + path_value
            )

        return StdioServerParameters(
            command=os.environ.get(
                "COMSPEC",
                r"C:\Windows\System32\cmd.exe",
            ),
            args=[
                "/c",
                "npx",
                "-y",
                "@modelcontextprotocol/server-filesystem",
                *allowed_directories,
            ],
            env={
                "PATH": path_value,
            },
        )

    def _chat_with_tools(self, user_text):
        return asyncio.run(
            self._chat_with_mcp(
                user_text
            )
        )

    async def _chat_with_mcp(self, user_text):
        messages = self._messages_for_prompt(
            user_text
        )

        active_project_root = (
            str(self.active_project_root.resolve())
            if self.active_project_root is not None
            else "Yok"
        )
        gakko_yuva_root = str(
            (
                PROJECT_ROOT
                / "GAKKO_YUVA"
            ).resolve()
        )

        messages.insert(
            1,
            {
                "role": "system",
                "content": (
                    "Çalışma bilgileri:\n"
                    f"- Aktif proje kökü: {active_project_root}\n"
                    f"- GAKKO_YUVA: {gakko_yuva_root}"
                ),
            },
        )

        server_parameters = (
            self._filesystem_server_parameters()
        )

        async with MCPClient(
            server_parameters
        ) as mcp_client:
            listed = await mcp_client.list_tools()

            mcp_tools = list(
                getattr(
                    listed,
                    "tools",
                    listed,
                )
                or []
            )

            mcp_tool_names = {
                str(tool.name)
                for tool in mcp_tools
            }

            tools = [
                *[
                    _mcp_tool_to_ollama(tool)
                    for tool in mcp_tools
                ],
                *INTERNET_TOOLS,
            ]

            print(
                "[MCP DOSYA SISTEMI] "
                f"{len(mcp_tools)} arac geldi.",
                flush=True,
            )

            return await self._tool_loop(
                messages,
                tools,
                mcp_client,
                mcp_tool_names,
            )

    async def _tool_loop(
        self,
        messages,
        tools,
        mcp_client,
        mcp_tool_names,
    ):
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

                if tool_name in mcp_tool_names:
                    print(
                        "[QWEN MCP] "
                        f"arac={tool_name} | "
                        f"arguments={arguments}",
                        flush=True,
                    )

                    mcp_result = (
                        await mcp_client.call_tool(
                            tool_name,
                            arguments=arguments,
                        )
                    )

                    result = (
                        _mcp_result_to_text(
                            mcp_result
                        )
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
