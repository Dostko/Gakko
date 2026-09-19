from __future__ import annotations

import os
import shutil
from pathlib import Path

from mcp import StdioServerParameters

from .Qwen_oturum.qwen_ayarlar import PROJECT_ROOT


def _git_runner():
    uvx_path = shutil.which("uvx")
    if uvx_path:
        return uvx_path, ["mcp-server-git"]

    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path, ["tool", "run", "mcp-server-git"]

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        packages_root = (
            Path(local_appdata)
            / "Microsoft"
            / "WinGet"
            / "Packages"
        )
        candidates = sorted(
            packages_root.glob(
                "astral-sh.uv_Microsoft.Winget.Source_*/uv.exe"
            )
        )
        if candidates:
            return str(candidates[0]), [
                "tool",
                "run",
                "mcp-server-git",
            ]

    raise RuntimeError(
        "Git MCP başlatılamadı: uv/uvx bulunamadı."
    )


def create_git_server_parameters(project_root, environment):
    command, args = _git_runner()
    return StdioServerParameters(
        command=command,
        args=[
            *args,
            "--repository",
            str(Path(project_root).resolve()),
        ],
        env=environment,
    )


async def load_git_tools(git_client, tool_schema):
    response = await git_client.list_tools()
    remote_tools = list(
        getattr(response, "tools", response) or ()
    )

    if not remote_tools:
        raise RuntimeError("Git MCP hiçbir araç sunmadı.")

    tools = [tool_schema(tool) for tool in remote_tools]
    names = frozenset(str(tool.name) for tool in remote_tools)
    return remote_tools, tools, names


def _prepare_git_arguments(arguments, project_root):
    prepared = dict(arguments)
    prepared["repo_path"] = str(Path(project_root).resolve())
    return prepared


async def call_git_tool(owner, runtime, name, arguments):
    arguments = _prepare_git_arguments(arguments, PROJECT_ROOT)
    return await owner._call_mcp_tool(
        runtime.git_client,
        name,
        arguments,
    )
