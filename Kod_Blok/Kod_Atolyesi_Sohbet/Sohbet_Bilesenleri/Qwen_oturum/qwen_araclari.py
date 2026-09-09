from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import os
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
                f"[MCP HAZIR] {len(remote_tools)} araç bulundu. "
                f"Qwen'e resmî araç formatında {len(mcp_tools)} MCP aracı sunuldu.",
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
            tool_path = str(arguments.get("path") or "").replace("\\", "/")
            print(
                f"[MCP BAŞLADI] {tool_path}".rstrip(),
                flush=True,
            )
            tool_started_at = time.perf_counter()
            try:
                result = await runtime.client.call_tool(
                    name,
                    arguments=arguments,
                )
                tool_text = _mcp_text(result)
            except Exception as exc:
                print(
                    "[MCP HATA] "
                    f"Süre: {time.perf_counter() - tool_started_at:.2f} sn | "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
                raise

            print(
                "[MCP TAMAMLANDI] "
                f"Süre: {time.perf_counter() - tool_started_at:.2f} sn | "
                f"Durum: {'Hata' if bool(getattr(result, 'is_error', False)) else 'Başarılı'} | "
                f"Sonuç: {len(tool_text)} karakter",
                flush=True,
            )

            if bool(getattr(result, "is_error", False)):
                print(f"[MCP HATA] {tool_text}", flush=True)
                return f"[MCP HATA] {tool_text}"

            return tool_text

        if name in INTERNET_TOOL_NAMES:
            return internet_araci_calistir(name, arguments)

        return f"[TOOL HATA] Bilinmeyen araç: {name}"

    async def _chat_with_tools(self, user_text, runtime):
        messages = self._messages_for_prompt(user_text)

        started_at = time.perf_counter()
        totals = self._measurement_totals()
        last_response = None
        rounds = 0

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
            self._add_measurement(totals, response)

            assistant_message = response.message
            messages.append(assistant_message)

            tool_calls = assistant_message.tool_calls or []

            if not tool_calls:
                self._emit_context_remaining(response)
                self._print_measurement(started_at, totals, rounds)
                return str(assistant_message.content or "").strip()

            for tool_call in tool_calls:
                if self._stopping or self._cancel_requested.is_set():
                    return _CANCELLED

                name = str(tool_call.function.name or "").strip()
                arguments = tool_call.function.arguments or {}

                if not name:
                    raise RuntimeError("Qwen araç çağrısında araç adı yok.")

                result = await self._execute_qwen_tool(
                    runtime,
                    name,
                    arguments,
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

        self._print_measurement(started_at, totals, rounds)

        raise RuntimeError(
            f"Qwen {MAX_TOOL_ROUNDS} araç turu içinde nihai cevap üretmedi."
        )
