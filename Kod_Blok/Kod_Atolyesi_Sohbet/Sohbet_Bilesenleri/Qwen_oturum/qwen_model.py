from __future__ import annotations

from .yapay_zeka_gecisi import model_chat


class QwenModelMixin:
    def _chat(self, **kwargs):
        return model_chat(
            self,
            **kwargs,
        )

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
