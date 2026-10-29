import json
import os
import socket

from PySide6.QtCore import QObject, Slot


class TerminalBridge(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self._main_window = main_window

    def _terminal_port(self):
        try:
            port = int(str(os.environ.get("GAKKO_TERMINAL_PORT", "")).strip())
        except ValueError:
            return None
        return port if 1 <= port <= 65535 else None

    @Slot(result=bool)
    def toggle_terminal(self):
        port = self._terminal_port()
        if port is None:
            return False

        frame = self._main_window.frameGeometry()
        command = {
            "action": "toggle",
            "main_x": int(frame.x()),
            "main_y": int(frame.y()),
            "main_width": int(frame.width()),
            "main_height": int(frame.height()),
        }
        payload = (json.dumps(command, separators=(",", ":")) + "\n").encode("utf-8")

        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3) as client:
                client.sendall(payload)
        except OSError:
            return False

        return True
