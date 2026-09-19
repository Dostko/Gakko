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
)
from ..git_kayitlari import (
    create_git_server_parameters,
    load_git_tools,
    resolve_git_repository,
)
from .qwen_ayarlar import (
    PROJECT_ROOT,
    QWEN_MD_PATH,
)


FILESYSTEM_HIDDEN_TOOLS = frozenset({"read_file", "search_files"})
RIPGREP_PACKAGE = "@atef_andrus/mcp-ripgrep@1.2.0"
RIPGREP_TOOL_NAMES = frozenset({"search"})
RIPGREP_MAX_RESULT_CHARS = 12000
RIPGREP_MAX_OUTPUT_BYTES = 1000000


@dataclass(slots=True)
class MCPRuntime:
    client: Client
    search_client: Client
    git_client: Client | None
    git_repo_root: Path | None
    tool_names: frozenset[str]
    search_tool_names: frozenset[str]
    git_tool_names: frozenset[str]
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


def _mcp_text(result, arguments=None):
    chunks = []
    path = ""

    if isinstance(arguments, dict):
        path = str(arguments.get("path") or "").replace("\\", "/")

    for item in getattr(result, "content", None) or ():
        value = getattr(item, "text", None)
        if isinstance(value, str) and value:
            chunks.append(value)
            continue

        item_type = str(getattr(item, "type", "") or "")
        if item_type in {"image", "audio"}:
            mime_type = (
                getattr(item, "mime_type", None)
                or getattr(item, "mimeType", None)
                or "application/octet-stream"
            )
            media_text = f"[MCP MEDYA] tür={item_type} | mime={mime_type}"
            if path:
                media_text += f" | yol={path}"
            chunks.append(media_text)
            continue

        if hasattr(item, "model_dump"):
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


class QwenMCPMixin:
    def _mcp_allowed_paths(self):
        candidates = [
            QWEN_MD_PATH.parent.resolve(),
            (PROJECT_ROOT / "GAKKO_YUVA").resolve(),
            Path("C:/").resolve(),
            Path("D:/").resolve(),
        ]

        if self.generated_images_root is not None:
            candidates.append(Path(self.generated_images_root).resolve())

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

    def _mcp_environment(self):
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

        return {"PATH": current_path}

    def _mcp_server_parameters(self):
        return StdioServerParameters(
            command=os.environ.get("COMSPEC", "cmd.exe"),
            args=[
                "/c",
                "npx",
                "-y",
                "@modelcontextprotocol/server-filesystem",
                *self._mcp_allowed_paths(),
            ],
            env=self._mcp_environment(),
        )

    def _ripgrep_server_parameters(self):
        args = [
            "/c",
            "npx",
            "-y",
            RIPGREP_PACKAGE,
        ]

        for path in self._mcp_allowed_paths():
            args.extend(["--allow-dir", path])

        args.extend(
            [
                "--max-result-chars",
                str(RIPGREP_MAX_RESULT_CHARS),
                "--max-output-bytes",
                str(RIPGREP_MAX_OUTPUT_BYTES),
            ]
        )

        return StdioServerParameters(
            command=os.environ.get("COMSPEC", "cmd.exe"),
            args=args,
            env=self._mcp_environment(),
        )

    @asynccontextmanager
    async def _git_mcp_client(self):
        project_root = (
            self.active_project_root
            if self.active_project_root is not None
            else PROJECT_ROOT
        )
        git_repo_root = resolve_git_repository(project_root)

        if git_repo_root is None:
            print(
                "[GIT DEVRE DIŞI] Aktif proje Git repository değil: "
                f"{Path(project_root).resolve()}",
                flush=True,
            )
            yield None, None
            return

        git_parameters = create_git_server_parameters(
            git_repo_root,
            self._mcp_environment(),
        )
        async with Client(git_parameters) as git_client:
            yield git_client, git_repo_root

    @asynccontextmanager
    async def _mcp_runtime(self):
        async with Client(self._mcp_server_parameters()) as client:
            async with Client(self._ripgrep_server_parameters()) as search_client:
                async with self._git_mcp_client() as (
                    git_client,
                    git_repo_root,
                ):
                    response = await client.list_tools()
                    remote_tools = list(
                        getattr(response, "tools", response) or ()
                    )
                    visible_tools = [
                        tool
                        for tool in remote_tools
                        if str(tool.name) not in FILESYSTEM_HIDDEN_TOOLS
                    ]

                    search_response = await search_client.list_tools()
                    remote_search_tools = list(
                        getattr(search_response, "tools", search_response) or ()
                    )
                    visible_search_tools = [
                        tool
                        for tool in remote_search_tools
                        if str(tool.name) in RIPGREP_TOOL_NAMES
                    ]

                    if not visible_search_tools:
                        raise RuntimeError(
                            "Ripgrep MCP 'search' aracını sunmadı."
                        )

                    if git_client is None:
                        remote_git_tools = []
                        git_tools = []
                        git_names = frozenset()
                    else:
                        remote_git_tools, git_tools, git_names = (
                            await load_git_tools(
                                git_client,
                                _mcp_tool_schema,
                            )
                        )

                    mcp_tools = [
                        _mcp_tool_schema(tool)
                        for tool in visible_tools
                    ]
                    search_tools = [
                        _mcp_tool_schema(tool)
                        for tool in visible_search_tools
                    ]
                    names = frozenset(
                        str(tool.name)
                        for tool in visible_tools
                    )
                    search_names = frozenset(
                        str(tool.name)
                        for tool in visible_search_tools
                    )
                    if search_names & names:
                        raise RuntimeError(
                            "Filesystem MCP ile Ripgrep MCP araç adları çakışıyor."
                        )

                    if search_names & INTERNET_TOOL_NAMES:
                        raise RuntimeError(
                            "Ripgrep MCP ile internet araç adları çakışıyor."
                        )

                    if git_names & names:
                        raise RuntimeError(
                            "Filesystem MCP ile Git MCP araç adları çakışıyor."
                        )

                    if git_names & search_names:
                        raise RuntimeError(
                            "Ripgrep MCP ile Git MCP araç adları çakışıyor."
                        )

                    if git_names & INTERNET_TOOL_NAMES:
                        raise RuntimeError(
                            "Git MCP ile internet araç adları çakışıyor."
                        )

                    tools = [
                        *mcp_tools,
                        *search_tools,
                        *git_tools,
                        *INTERNET_TOOLS,
                    ]

                    print(
                        f"[MCP HAZIR] {len(remote_tools)} Filesystem aracı bulundu; "
                        f"{len(mcp_tools)} tanesi Qwen'e sunuldu. "
                        f"{len(git_tools)} Git aracı Qwen'e sunuldu. "
                        "Eski search_files kaldırıldı; Ripgrep search etkin.",
                        flush=True,
                    )

                    yield MCPRuntime(
                        client=client,
                        search_client=search_client,
                        git_client=git_client,
                        git_repo_root=git_repo_root,
                        tool_names=names,
                        search_tool_names=search_names,
                        git_tool_names=git_names,
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

    async def _call_mcp_tool(self, client, name, arguments):
        tool_path = str(arguments.get("path") or "").replace("\\", "/")
        print(
            f"[MCP BAŞLADI] {name} | {tool_path}".rstrip(" |"),
            flush=True,
        )
        tool_started_at = time.perf_counter()

        try:
            result = await client.call_tool(
                name,
                arguments=arguments,
            )
            tool_text = _mcp_text(result, arguments)
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
