from __future__ import annotations

import multiprocessing

from ollama import ChatResponse, Client

from .qwen_ayarlar import (
    OLLAMA_HOST,
    _CANCELLED,
)


def _ollama_chat_worker(connection, chat_arguments):
    client = None

    try:
        client = Client(host=OLLAMA_HOST)
        response = client.chat(**chat_arguments)

        if hasattr(response, "model_dump"):
            payload = response.model_dump(mode="json")
        elif hasattr(response, "dict"):
            payload = response.dict()
        else:
            payload = dict(response)

        connection.send(("ok", payload))

    except BaseException as error:
        try:
            connection.send(
                ("error", f"{type(error).__name__}: {error}")
            )
        except (BrokenPipeError, EOFError, OSError):
            pass

    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

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
            target=_ollama_chat_worker,
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
                        return ChatResponse(**payload)

                    if status == "error":
                        raise RuntimeError(payload)

                if not process.is_alive():
                    if receive_connection.poll(0.1):
                        continue

                    raise RuntimeError(
                        "Qwen istek süreci yanıt vermeden kapandı "
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