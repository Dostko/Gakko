from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

from mcp import StdioServerParameters

from .Qwen_oturum.qwen_ayarlar import PROJECT_ROOT


GIT_PUSH_TOOL_NAME = "git_push"
GIT_PUSH_TOOL = {
    "type": "function",
    "function": {
        "name": GIT_PUSH_TOOL_NAME,
        "description": (
            "Aktif master branch'ini origin/master uzak dalına gönderir. "
            "Yalnız kullanıcı açıkça onay verdikten sonra kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


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

    if GIT_PUSH_TOOL_NAME not in names:
        tools.append(GIT_PUSH_TOOL)
        names = names | {GIT_PUSH_TOOL_NAME}

    return remote_tools, tools, names


def _prepare_git_arguments(arguments, project_root):
    prepared = dict(arguments)
    prepared["repo_path"] = str(Path(project_root).resolve())
    return prepared


def push_active_master(repo_path, runner=subprocess.run):
    repo = str(Path(repo_path).resolve())
    run_options = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "check": False,
    }

    branch_result = runner(
        ["git", "-C", repo, "branch", "--show-current"],
        **run_options,
    )
    if branch_result.returncode != 0:
        detail = (branch_result.stderr or branch_result.stdout).strip()
        return f"[GIT HATA] Aktif branch okunamadı: {detail}"

    branch = branch_result.stdout.strip()
    if branch != "master":
        return (
            "[GIT HATA] Push durduruldu: aktif branch "
            f"'{branch or 'bilinmiyor'}'; beklenen branch 'master'."
        )

    push_result = runner(
        ["git", "-C", repo, "push", "origin", "master"],
        **run_options,
    )
    detail = (push_result.stdout or push_result.stderr).strip()
    if push_result.returncode != 0:
        return f"[GIT HATA] Git push başarısız: {detail}"

    return f"[GIT PUSH BAŞARILI] origin/master\n{detail}".rstrip()


async def call_git_tool(owner, runtime, name, arguments):
    arguments = _prepare_git_arguments(arguments, PROJECT_ROOT)

    if name == GIT_PUSH_TOOL_NAME:
        return await asyncio.to_thread(
            push_active_master,
            arguments["repo_path"],
        )

    result = await owner._call_mcp_tool(
        runtime.git_client,
        name,
        arguments,
    )

    if name == "git_commit":
        return (
            f"{result}\n\n"
            "[GIT AKIŞI] Commit başarılıysa cevabı bitirme. "
            "Kullanıcıya tam olarak 'Git push yapmamı "
            "onaylıyor musunuz?' diye sor. Kullanıcı açıkça "
            "onay vermeden git_push aracını kullanma."
        )

    return result
