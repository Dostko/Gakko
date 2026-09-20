from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path

from mcp import StdioServerParameters

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
GIT_COMMIT_SUCCESS_PATTERNS = (
    r"\bcommit\b.{0,80}\b(başarıyla|başarılı|tamamlandı|gerçekleştirildi|oluşturuldu)",
    r"\bgit kayd[ıi]\b.{0,80}\b(alındı|başarıyla|başarılı|tamamlandı|oluşturuldu)",
    r"\bcommit\b.{0,80}\b(successfully|successful|completed|created)",
)


def guard_git_commit_claim(text, git_commit_verified):
    final_text = str(text or "").strip()

    if git_commit_verified:
        return final_text

    normalized = final_text.casefold()
    claims_success = any(
        re.search(pattern, normalized, flags=re.DOTALL)
        for pattern in GIT_COMMIT_SUCCESS_PATTERNS
    )

    if not claims_success:
        return final_text

    return (
        "[GIT HATA] Git commit bu turda Git aracıyla "
        "doğrulanmadı. Başarı bildirimi engellendi."
    )


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


def resolve_git_repository(project_root, runner=subprocess.run):
    project_path = str(Path(project_root).resolve())
    result = runner(
        [
            "git",
            "-C",
            project_path,
            "rev-parse",
            "--show-toplevel",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        return None

    repository_root = result.stdout.strip()
    if not repository_root:
        return None

    return Path(repository_root).resolve()


def initialize_git_repository(project_root, runner=subprocess.run):
    project_path = Path(project_root).resolve()
    result = runner(
        [
            "git",
            "-C",
            str(project_path),
            "init",
            "-b",
            "master",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"Git repository oluşturulamadı: {detail}"
        )

    return project_path


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


def _read_head_commit(repo_path, runner=subprocess.run):
    result = runner(
        [
            "git",
            "-C",
            str(Path(repo_path).resolve()),
            "rev-parse",
            "HEAD",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        return None

    commit_id = result.stdout.strip()
    return commit_id or None


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


async def call_git_tool(
    owner,
    runtime,
    name,
    arguments,
    runner=subprocess.run,
):
    arguments = _prepare_git_arguments(
        arguments,
        runtime.git_repo_root,
    )

    if name == GIT_PUSH_TOOL_NAME:
        return await asyncio.to_thread(
            push_active_master,
            arguments["repo_path"],
        )

    commit_before = None
    if name == "git_commit":
        commit_before = await asyncio.to_thread(
            _read_head_commit,
            arguments["repo_path"],
            runner,
        )

    result = await owner._call_mcp_tool(
        runtime.git_client,
        name,
        arguments,
    )

    if name == "git_commit":
        result_text = str(result or "").strip()
        if result_text.startswith(("[MCP HATA]", "[GIT HATA]")):
            return (
                "[GIT HATA] Git commit aracı hata döndürdü; "
                "push onayı istenmedi.\n"
                f"{result_text}"
            )

        commit_after = await asyncio.to_thread(
            _read_head_commit,
            arguments["repo_path"],
            runner,
        )

        if commit_after is None or commit_after == commit_before:
            return (
                "[GIT HATA] Git commit doğrulanamadı; "
                "deponun HEAD kimliği değişmedi. Push onayı istenmedi."
            )

        result_prefix = f"{result_text}\n\n" if result_text else ""
        return (
            f"{result_prefix}"
            f"[GIT COMMIT DOĞRULANDI] {commit_after}\n\n"
            "[GIT AKIŞI] Commit başarılıysa cevabı bitirme. "
            "Kullanıcıya tam olarak 'Git push yapmamı "
            "onaylıyor musunuz?' diye sor. Kullanıcı açıkça "
            "onay vermeden git_push aracını kullanma."
        )

    return result
