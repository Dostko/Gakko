from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import os
import re
import time
from pathlib import Path

from mcp import Client, StdioServerParameters

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
    QWEN_MD_PATH,
    _CANCELLED,
)


_TOOL_CALL_PATTERN = re.compile(
    r"<tool_call>\s*(.*?)\s*</tool_call>",
    re.DOTALL,
)


@dataclass(slots=True)
class MCPRuntime:
    client: Client
    tool_names: frozenset[str]
    tools: list[dict]


def _tool_input_schema(tool):
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)

    if hasattr(schema, "model_dump"):
        schema = schema.model_dump(by_alias=True)

    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}}

    return schema


def _mcp_tool_schema(tool):
    return {
        "type": "function",
        "function": {
            "name": str(tool.name),
            "description": str(getattr(tool, "description", "") or ""),
            "parameters": _tool_input_schema(tool),
        },
    }


def _qwen_tool_prompt(tools):
    tool_lines = "\n".join(
        json.dumps(tool, ensure_ascii=False, separators=(",", ":"))
        for tool in tools
    )

    return (
        "# Tools\n\n"
        "Kullanabileceğin araç şemaları <tools> etiketleri içindedir.\n"
        "Bir araca ihtiyaç duyduğunda bir veya daha fazla çağrıyı "
        "<tool_call> etiketleri içinde JSON olarak üret.\n"
        "<tools>\n"
        f"{tool_lines}\n"
        "</tools>\n\n"
        "Çağrı biçimi:\n"
        "<tool_call>\n"
        '{"name":"function_name","arguments":{}}\n'
        "</tool_call>"
    )


def _parse_qwen_tool_calls(content):
    text = str(content or "")

    if "<think>" in text and "</think>" not in text:
        return []

    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1]

    blocks = _TOOL_CALL_PATTERN.findall(text)
    calls = []

    for block in blocks:
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"Qwen geçersiz araç çağrısı üretti: {error}"
            ) from error

        if not isinstance(payload, dict):
            raise RuntimeError("Qwen araç çağrısı JSON nesnesi olmalı.")

        name = str(payload.get("name") or "").strip()
        arguments = payload.get("arguments", {})

        if not name:
            raise RuntimeError("Qwen araç çağrısında araç adı yok.")

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Qwen araç argümanları geçersiz JSON: {error}"
                ) from error

        if not isinstance(arguments, dict):
            raise RuntimeError("Qwen araç argümanları JSON nesnesi olmalı.")

        calls.append((name, arguments))

    if "<tool_call>" in text and not calls:
        raise RuntimeError("Qwen araç çağrısı tamamlanamadı.")

    return calls


def _qwen_tool_response_message(results):
    content = "\n".join(
        f"<tool_response>\n{result}\n</tool_response>"
        for result in results
    )
    return {"role": "user", "content": content}


def _mcp_text(result):
    chunks = []

    for item in getattr(result, "content", None) or ():
        value = getattr(item, "text", None)
        if isinstance(value, str) and value:
            chunks.append(value)
        elif hasattr(item, "model_dump"):
            chunks.append(
                json.dumps(
                    item.model_dump(mode="json", by_alias=True),
                    ensure_ascii=False,
                )
            )

    if not chunks:
        structured = getattr(result, "structured_content", None)
        if structured is not None:
            chunks.append(json.dumps(structured, ensure_ascii=False))

    return "\n".join(chunks).strip()


class QwenAraclariMixin:
    def _measurement_totals(self):
        return {
            key: 0
            for key in (
                "total_duration",
                "load_duration",
                "prompt_eval_count",
                "prompt_eval_duration",
                "eval_count",
                "eval_duration",
            )
        }

    def _add_measurement(self, totals, response):
        for key in totals:
            try:
                totals[key] += int(getattr(response, key, 0) or 0)
            except (TypeError, ValueError):
                pass

    def _emit_context_remaining(self, response):
        try:
            used = int(getattr(response, "prompt_eval_count", 0) or 0)
            used += int(getattr(response, "eval_count", 0) or 0)
            used = min(max(used, 0), OLLAMA_CONTEXT_SIZE)
            remaining = 100.0 * (1.0 - (used / OLLAMA_CONTEXT_SIZE))
            self.context_remaining.emit(min(max(remaining, 0.0), 100.0))
        except Exception:
            pass

    def _print_measurement(self, started_at, totals, rounds):
        elapsed = time.perf_counter() - started_at
        model_seconds = totals["total_duration"] / 1_000_000_000
        load_seconds = totals["load_duration"] / 1_000_000_000
        prompt_seconds = totals["prompt_eval_duration"] / 1_000_000_000
        eval_seconds = totals["eval_duration"] / 1_000_000_000
        eval_count = totals["eval_count"]
        speed = eval_count / eval_seconds if eval_seconds > 0 else 0.0

        print(
            "[QWEN ÖLÇÜM] "
            f"toplam={elapsed:.2f} sn | "
            f"model={model_seconds:.2f} sn | "
            f"yükleme={load_seconds:.2f} sn | "
            f"giriş={prompt_seconds:.2f} sn / "
            f"{totals['prompt_eval_count']} tok | "
            f"üretim={eval_seconds:.2f} sn / "
            f"{eval_count} tok / "
            f"{speed:.1f} tok/sn | "
            f"tur={rounds}",
            flush=True,
        )

    def _mcp_allowed_paths(self):
        candidates = [
            QWEN_MD_PATH.parent.resolve(),
            (PROJECT_ROOT / "GAKKO_YUVA").resolve(),
        ]

        if self.active_project_root is not None:
            candidates.append(Path(self.active_project_root).resolve())

        unique = []
        seen = set()

        for path in candidates:
            key = str(path).casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append(str(path))

        return unique

    def _mcp_server_parameters(self):
        current_path = os.environ.get("PATH", "")
        default_node_dir = (
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "nodejs"
        )
        node_path = str(default_node_dir)

        if node_path.casefold() not in current_path.casefold():
            current_path = (
                f"{current_path}{os.pathsep}{node_path}"
                if current_path
                else node_path
            )

        return StdioServerParameters(
            command=os.environ.get("COMSPEC", "cmd.exe"),
            args=[
                "/c",
                "npx",
                "-y",
                "@modelcontextprotocol/server-filesystem",
                *self._mcp_allowed_paths(),
            ],
            env={"PATH": current_path},
        )

    @asynccontextmanager
    async def _mcp_runtime(self):
        async with Client(self._mcp_server_parameters()) as client:
            response = await client.list_tools()
            remote_tools = list(getattr(response, "tools", response) or ())
            visible_tools = [
                tool
                for tool in remote_tools
                if str(tool.name) != "read_file"
            ]
            mcp_tools = [_mcp_tool_schema(tool) for tool in visible_tools]
            names = frozenset(str(tool.name) for tool in visible_tools)
            tools = [*mcp_tools, *INTERNET_TOOLS]

            print(
                f"[MCP DOSYA SISTEMI] {len(remote_tools)} arac geldi. "
                f"Qwen resmi arac formatinda {len(mcp_tools)} MCP araci kullaniyor.",
                flush=True,
            )

            yield MCPRuntime(
                client=client,
                tool_names=names,
                tools=tools,
            )

    async def _mcp_read_text(self, runtime, path):
        result = await runtime.client.call_tool(
            "read_text_file",
            arguments={"path": str(path)},
        )

        text = _mcp_text(result)

        if bool(getattr(result, "is_error", False)):
            raise RuntimeError(text or f"Dosya okunamadı: {path}")

        if not text:
            raise RuntimeError(f"Dosya boş veya okunamadı: {path}")

        return text

    async def _execute_qwen_tool(self, runtime, name, arguments):
        if name in runtime.tool_names:
            print(
                f"[QWEN MCP] arac={name} | arguments={arguments}",
                flush=True,
            )
            result = await runtime.client.call_tool(
                name,
                arguments=arguments,
            )
            tool_text = _mcp_text(result)

            if bool(getattr(result, "is_error", False)):
                return f"[MCP HATA] {tool_text}"

            return tool_text

        if name in INTERNET_TOOL_NAMES:
            return internet_araci_calistir(name, arguments)

        return f"[TOOL HATA] Bilinmeyen araç: {name}"

    async def _chat_with_tools(self, user_text, runtime):
        messages = self._messages_for_prompt(user_text)
        messages[0] = dict(messages[0])
        messages[0]["content"] = (
            f"{messages[0]['content']}\n\n"
            f"{_qwen_tool_prompt(runtime.tools)}"
        )

        started_at = time.perf_counter()
        totals = self._measurement_totals()
        last_response = None
        rounds = 0

        for _ in range(MAX_TOOL_ROUNDS):
            if self._stopping:
                return None

            if self._cancel_requested.is_set():
                return _CANCELLED

            response = self._chat(
                model=OLLAMA_MODEL,
                messages=messages,
                stream=False,
                options={"num_ctx": OLLAMA_CONTEXT_SIZE},
            )

            if response is _CANCELLED:
                return _CANCELLED

            last_response = response
            rounds += 1
            self._add_measurement(totals, response)

            assistant_content = str(response.message.content or "").strip()
            messages.append(
                {"role": "assistant", "content": assistant_content}
            )
            calls = _parse_qwen_tool_calls(assistant_content)

            if not calls:
                self._emit_context_remaining(response)
                self._print_measurement(started_at, totals, rounds)
                return assistant_content

            results = []

            for name, arguments in calls:
                if self._stopping or self._cancel_requested.is_set():
                    return _CANCELLED

                results.append(
                    await self._execute_qwen_tool(
                        runtime,
                        name,
                        arguments,
                    )
                )

            messages.append(_qwen_tool_response_message(results))

        if last_response is not None:
            self._emit_context_remaining(last_response)

        self._print_measurement(started_at, totals, rounds)

        raise RuntimeError(
            f"Qwen {MAX_TOOL_ROUNDS} araç turu içinde nihai cevap üretmedi."
        )
