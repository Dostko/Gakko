from __future__ import annotations

import json
import multiprocessing
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .qwen_ayarlar import (
    STRATA_API_MODEL,
    STRATA_CHAT_URL,
    _CANCELLED,
)


@dataclass
class _StrataToolFunction:
    name: str
    arguments: dict


@dataclass
class _StrataToolCall:
    id: str
    function: _StrataToolFunction
    type: str = "function"

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "function": {
                "name": self.function.name,
                "arguments": json.dumps(
                    self.function.arguments,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        }


@dataclass
class _StrataMessage:
    role: str = "assistant"
    content: str = ""
    tool_calls: list[_StrataToolCall] = field(default_factory=list)

    def to_dict(self):
        result = {
            "role": self.role,
            "content": self.content,
        }
        if self.tool_calls:
            result["tool_calls"] = [
                tool_call.to_dict()
                for tool_call in self.tool_calls
            ]
        return result


@dataclass
class _StrataChatResponse:
    message: _StrataMessage
    prompt_eval_count: int = 0
    eval_count: int = 0


def _tool_arguments(value):
    if isinstance(value, dict):
        return value

    raw = str(value or "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Strata araç argümanları geçerli JSON değil: {raw[:240]}"
        ) from error

    if not isinstance(parsed, dict):
        raise RuntimeError("Strata araç argümanları JSON nesnesi olmalı.")

    return parsed


def _message_to_dict(message):
    if hasattr(message, "to_dict"):
        message = message.to_dict()
    elif not isinstance(message, dict):
        role = str(getattr(message, "role", "") or "").strip()
        content = getattr(message, "content", "")
        tool_calls = getattr(message, "tool_calls", None)
        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls

    result = dict(message)
    images = result.pop("images", None) or []

    if images:
        parts = [
            {
                "type": "image_url",
                "image_url": {"url": str(image_path)},
            }
            for image_path in images
        ]
        content = result.get("content")
        if content not in (None, ""):
            parts.append({"type": "text", "text": str(content)})
        result["content"] = parts

    tool_calls = result.get("tool_calls")
    if tool_calls:
        normalized = []
        for tool_call in tool_calls:
            if hasattr(tool_call, "to_dict"):
                normalized.append(tool_call.to_dict())
            elif isinstance(tool_call, dict):
                item = dict(tool_call)
                function = dict(item.get("function") or {})
                arguments = function.get("arguments")
                if isinstance(arguments, dict):
                    function["arguments"] = json.dumps(
                        arguments,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                item["function"] = function
                normalized.append(item)
        result["tool_calls"] = normalized

    return result


def _build_strata_payload(chat_arguments):
    arguments = dict(chat_arguments)
    think = arguments.pop("think", None)
    arguments.pop("options", None)
    arguments.pop("keep_alive", None)
    arguments.pop("model", None)

    messages = arguments.pop("messages", [])
    payload = {
        "model": STRATA_API_MODEL,
        "messages": [_message_to_dict(message) for message in messages],
        "stream": bool(arguments.pop("stream", False)),
    }

    tools = arguments.pop("tools", None)
    if tools:
        payload["tools"] = tools

    if think is True:
        payload["reasoning_effort"] = "high"
    elif think is False:
        payload["reasoning_effort"] = "none"

    for key in (
        "temperature",
        "top_p",
        "max_tokens",
        "seed",
        "stop",
        "tool_choice",
    ):
        if key in arguments:
            payload[key] = arguments[key]

    return payload


def _parse_strata_response(payload):
    choices = payload.get("choices") or []
    if not choices:
        error = payload.get("error")
        if isinstance(error, dict):
            detail = error.get("message") or str(error)
        else:
            detail = str(error or "Strata boş yanıt döndürdü.")
        raise RuntimeError(detail)

    raw_message = choices[0].get("message") or {}
    tool_calls = []

    for item in raw_message.get("tool_calls") or []:
        function = item.get("function") or {}
        tool_calls.append(
            _StrataToolCall(
                id=str(item.get("id") or ""),
                type=str(item.get("type") or "function"),
                function=_StrataToolFunction(
                    name=str(function.get("name") or ""),
                    arguments=_tool_arguments(function.get("arguments")),
                ),
            )
        )

    usage = payload.get("usage") or {}
    return _StrataChatResponse(
        message=_StrataMessage(
            role=str(raw_message.get("role") or "assistant"),
            content=str(raw_message.get("content") or ""),
            tool_calls=tool_calls,
        ),
        prompt_eval_count=int(usage.get("prompt_tokens") or 0),
        eval_count=int(usage.get("completion_tokens") or 0),
    )


def _strata_chat_worker(connection, chat_arguments):
    try:
        payload = _build_strata_payload(chat_arguments)
        request = Request(
            STRATA_CHAT_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(request, timeout=1800) as response:
            raw = response.read().decode("utf-8")

        connection.send(("ok", json.loads(raw)))

    except HTTPError as error:
        try:
            detail = error.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(error)
        try:
            connection.send(("error", f"HTTP {error.code}: {detail}"))
        except (BrokenPipeError, EOFError, OSError):
            pass

    except (URLError, OSError, ValueError, RuntimeError) as error:
        try:
            connection.send(("error", f"{type(error).__name__}: {error}"))
        except (BrokenPipeError, EOFError, OSError):
            pass

    except BaseException as error:
        try:
            connection.send(("error", f"{type(error).__name__}: {error}"))
        except (BrokenPipeError, EOFError, OSError):
            pass

    finally:
        connection.close()


class QwenModelMixin:
    def _chat(self, **kwargs):
        if self._stopping or self._cancel_requested.is_set():
            return _CANCELLED

        process_context = multiprocessing.get_context("spawn")
        receive_connection, send_connection = process_context.Pipe(
            duplex=False
        )
        process = process_context.Process(
            target=_strata_chat_worker,
            args=(send_connection, dict(kwargs)),
            daemon=True,
        )
        started = False

        try:
            with self._active_process_lock:
                if self._stopping or self._cancel_requested.is_set():
                    return _CANCELLED

                self._active_process = process
                process.start()
                started = True

            send_connection.close()

            while True:
                if self._stopping or self._cancel_requested.is_set():
                    if process.is_alive():
                        process.terminate()
                    return _CANCELLED

                if receive_connection.poll(0.05):
                    try:
                        status, payload = receive_connection.recv()
                    except EOFError:
                        status = None
                        payload = None

                    if status == "ok":
                        return _parse_strata_response(payload)

                    if status == "error":
                        raise RuntimeError(payload)

                if not process.is_alive():
                    if receive_connection.poll(0.1):
                        continue

                    raise RuntimeError(
                        "Strata istek süreci yanıt vermeden kapandı "
                        f"(çıkış kodu: {process.exitcode})."
                    )

        finally:
            with self._active_process_lock:
                if self._active_process is process:
                    self._active_process = None

            if started and process.is_alive():
                process.terminate()

            if started:
                process.join(2.0)
                if process.is_alive() and hasattr(process, "kill"):
                    process.kill()
                    process.join(2.0)

            receive_connection.close()
            if not started:
                send_connection.close()

    def cancel_current(self):
        self._cancel_requested.set()

        with self._active_process_lock:
            active_process = self._active_process

        if active_process is None:
            return True

        try:
            if active_process.is_alive():
                active_process.terminate()
        except (OSError, ValueError):
            return False

        return True
