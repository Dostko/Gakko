from __future__ import annotations

import ctypes
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QPlainTextEdit, QVBoxLayout, QWidget


TERMINAL_WINDOW_TITLE = "GAKKO Terminali"
TERMINAL_HEIGHT = 280


def _console_python_executable() -> str:
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        console_executable = executable.with_name("python.exe")
        if console_executable.is_file():
            return str(console_executable)
    return str(executable)


def _apply_windows_dark_titlebar(window: QWidget) -> None:
    if os.name != "nt":
        return

    try:
        hwnd = int(window.winId())
        dwmapi = ctypes.WinDLL("dwmapi")

        dark_mode = ctypes.c_int(1)
        black = ctypes.c_uint(0x000000)
        white = ctypes.c_uint(0x00FFFFFF)

        for attribute, value in (
            (20, dark_mode),
            (34, black),
            (35, black),
            (36, white),
        ):
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
    except (AttributeError, OSError, ValueError):
        pass


class ProcessOutputThread(QThread):
    line_ready = Signal(str)
    process_finished = Signal(int)

    def __init__(self, process: subprocess.Popen, parent=None):
        super().__init__(parent)
        self._process = process

    def run(self):
        stream = self._process.stdout
        if stream is not None:
            for line in stream:
                self.line_ready.emit(line.rstrip("\r\n"))

        self.process_finished.emit(self._process.wait())


class TerminalControlThread(QThread):
    command_ready = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(4)
        self.port = int(self._server.getsockname()[1])
        self._stopping = False

    def run(self):
        while not self._stopping:
            try:
                connection, _address = self._server.accept()
            except OSError:
                break

            with connection:
                chunks = []
                total = 0
                while total < 65536:
                    part = connection.recv(4096)
                    if not part:
                        break
                    chunks.append(part)
                    total += len(part)
                    if b"\n" in part:
                        break

            if not chunks:
                continue

            try:
                raw = b"".join(chunks).split(b"\n", 1)[0]
                command = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            if command.get("action") == "__stop__":
                break

            self.command_ready.emit(command)

    def stop(self):
        if self._stopping:
            return

        self._stopping = True
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=0.25) as client:
                client.sendall(b'{"action":"__stop__"}\n')
        except OSError:
            pass

        self.wait(1500)
        try:
            self._server.close()
        except OSError:
            pass


class GakkoTerminalWindow(QWidget):
    def __init__(self):
        super().__init__()

        self._close_to_hide = False
        self.setWindowTitle(TERMINAL_WINDOW_TITLE)
        self.resize(900, TERMINAL_HEIGHT)
        self.setMinimumHeight(150)

        title = QLabel("GAKKO Terminali")
        title.setObjectName("terminalTitle")

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setUndoRedoEnabled(False)
        self.output.document().setMaximumBlockCount(5000)

        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(10)
        self.output.setFont(font)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(self.output, 1)

        self.setStyleSheet(
            """
            QWidget {
                background: #080b11;
                color: #d8dde5;
            }
            QLabel#terminalTitle {
                color: #f0f2f5;
                font-size: 13px;
                font-weight: 700;
            }
            QPlainTextEdit {
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
                background: #030507;
                color: #cfd7e3;
                padding: 8px;
                selection-background-color: #244d78;
            }
            """
        )

    @Slot(str)
    def append_output(self, text: str):
        value = str(text or "")
        if value:
            self.output.appendPlainText(value)

    def set_close_to_hide(self, enabled: bool):
        self._close_to_hide = bool(enabled)

    def _place_below_main(self, command: dict) -> None:
        left = int(command.get("main_x", 0))
        top = int(command.get("main_y", 0)) + int(command.get("main_height", 0))
        width = max(640, int(command.get("main_width", 900)))
        height = TERMINAL_HEIGHT

        if os.name == "nt":
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            user32.SetWindowPos.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_uint,
            ]
            user32.SetWindowPos.restype = ctypes.c_int

            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            user32.SetWindowPos(
                ctypes.c_void_p(hwnd),
                None,
                left,
                top,
                width,
                height,
                SWP_NOZORDER | SWP_NOACTIVATE,
            )
            return

        self.setGeometry(left, top, width, height)

    @Slot(object)
    def handle_control_command(self, command):
        if not isinstance(command, dict) or command.get("action") != "toggle":
            return

        if self.isMinimized():
            self.showNormal()
            self._place_below_main(command)
            self.raise_()
            self.activateWindow()
            return

        if self.isVisible():
            self.hide()
            return

        left = int(command.get("main_x", 0))
        top = int(command.get("main_y", 0)) + int(command.get("main_height", 0))
        width = max(640, int(command.get("main_width", 900)))
        self.setGeometry(left, top, width, TERMINAL_HEIGHT)
        self.show()
        self._place_below_main(command)
        _apply_windows_dark_titlebar(self)
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self._close_to_hide:
            event.ignore()
            self.hide()
            return
        super().closeEvent(event)


class GakkoLauncher(QObject):
    def __init__(self, terminal: GakkoTerminalWindow, chat_file: Path):
        super().__init__(terminal)
        self.terminal = terminal
        self.chat_file = Path(chat_file)
        self.process: subprocess.Popen | None = None
        self.output_thread: ProcessOutputThread | None = None
        self.control_thread = TerminalControlThread(self.terminal)
        self.control_thread.command_ready.connect(self.terminal.handle_control_command)

    def start(self):
        self.control_thread.start()

        if not self.chat_file.is_file():
            self.terminal.append_output(
                f"[GAKKO HATA] Sohbet dosyası bulunamadı: {self.chat_file}"
            )
            self.terminal.set_close_to_hide(False)
            self.terminal.show()
            _apply_windows_dark_titlebar(self.terminal)
            return

        env = os.environ.copy()
        env["GAKKO_TERMINAL_PORT"] = str(self.control_thread.port)
        env["PYTHONIOENCODING"] = "utf-8"

        command = [_console_python_executable(), "-u", str(self.chat_file)]
        creationflags = 0
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(self.chat_file.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
                creationflags=creationflags,
            )
        except Exception as error:
            self.terminal.append_output(f"[GAKKO HATA] Başlatılamadı: {error}")
            self.terminal.set_close_to_hide(False)
            self.terminal.show()
            _apply_windows_dark_titlebar(self.terminal)
            return

        self.terminal.set_close_to_hide(True)
        self.terminal.append_output("[GAKKO] Başlatıldı.")

        self.output_thread = ProcessOutputThread(self.process, self.terminal)
        self.output_thread.line_ready.connect(self.terminal.append_output)
        self.output_thread.process_finished.connect(self._on_process_finished)
        self.output_thread.start()

    @Slot(int)
    def _on_process_finished(self, exit_code: int):
        self.terminal.set_close_to_hide(False)

        if int(exit_code) == 0:
            app = QApplication.instance()
            if app is not None:
                app.quit()
            return

        self.terminal.append_output(
            f"[GAKKO HATA] Ana uygulama kapandı. Çıkış kodu: {exit_code}"
        )
        self.terminal.show()
        _apply_windows_dark_titlebar(self.terminal)
        self.terminal.raise_()
        self.terminal.activateWindow()

    def shutdown(self):
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)

        if self.output_thread is not None and self.output_thread.isRunning():
            self.output_thread.wait(2000)

        self.control_thread.stop()


def run_terminal_launcher(chat_file: Path) -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Gakko")

    terminal = GakkoTerminalWindow()
    launcher = GakkoLauncher(terminal, Path(chat_file))

    app.aboutToQuit.connect(launcher.shutdown)
    launcher.start()

    app._gakko_terminal = terminal
    app._gakko_launcher = launcher

    return app.exec()
