import ctypes
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from PySide6.QtCore import QEvent, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu
from PySide6.QtWebEngineCore import (
    QWebEngineContextMenuRequest,
    QWebEnginePage,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from Sohbet_Bilesenleri.sohbet_koprusu import ChatBridge


def _load_records_bridge_class():
    helper_path = (
        Path(__file__).resolve().parent
        / "Sohbet_Bilesenleri"
        / "sohbet_koprusu"
        / "kayitlar_koprusu.py"
    )
    spec = spec_from_file_location("gakko_kayitlar_koprusu", helper_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Kayıtlar köprüsü yüklenemedi: {helper_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.KayitlarKoprusu


KayitlarKoprusu = _load_records_bridge_class()
def _apply_windows_dark_titlebar(window):
    if sys.platform != "win32":
        return

    hwnd = int(window.winId())
    dwmapi = ctypes.WinDLL("dwmapi")

    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWA_BORDER_COLOR = 34
    DWMWA_CAPTION_COLOR = 35
    DWMWA_TEXT_COLOR = 36

    dark_mode = ctypes.c_int(1)

    black = ctypes.c_uint(0x000000)
    white = ctypes.c_uint(0x00FFFFFF)

    dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_USE_IMMERSIVE_DARK_MODE,
        ctypes.byref(dark_mode),
        ctypes.sizeof(dark_mode),
    )

    dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_CAPTION_COLOR,
        ctypes.byref(black),
        ctypes.sizeof(black),
    )

    dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_TEXT_COLOR,
        ctypes.byref(white),
        ctypes.sizeof(white),
    )

    dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_BORDER_COLOR,
        ctypes.byref(black),
        ctypes.sizeof(black),
    )

class AttachmentWebView(QWebEngineView):
    DROP_ZONE_HEIGHT = 240

    def __init__(self, on_files_dropped, parent=None):
        super().__init__(parent)
        self._on_files_dropped = on_files_dropped
        self.setAcceptDrops(True)
        self.loadFinished.connect(self._install_drop_event_filter)

    @staticmethod
    def _file_paths(event):
        mime_data = event.mimeData()
        if mime_data is None or not mime_data.hasUrls():
            return []

        file_paths = []
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue

            path = Path(url.toLocalFile())
            if not path.is_file():
                continue

            file_paths.append(str(path))

        return file_paths

    def _inside_composer_drop_zone(self, event):
        try:
            y = float(event.position().y())
        except (AttributeError, TypeError, ValueError):
            return False

        return y >= max(0, self.height() - self.DROP_ZONE_HEIGHT)

    def _install_drop_event_filter(self, _ok=True):
        proxy = self.focusProxy()
        if proxy is None:
            return
        proxy.setAcceptDrops(True)
        proxy.installEventFilter(self)

    def eventFilter(self, watched, event):
        event_type = event.type()
        if event_type not in {
            QEvent.Type.DragEnter,
            QEvent.Type.DragMove,
            QEvent.Type.Drop,
        }:
            return super().eventFilter(watched, event)

        file_paths = self._file_paths(event)
        if not file_paths:
            return super().eventFilter(watched, event)

        if event_type == QEvent.Type.DragEnter:
            event.acceptProposedAction()
            return True

        if event_type == QEvent.Type.DragMove:
            if self._inside_composer_drop_zone(event):
                event.acceptProposedAction()
            else:
                event.ignore()
            return True

        if self._inside_composer_drop_zone(event):
            self._on_files_dropped(file_paths[:1])
            event.acceptProposedAction()
        else:
            event.ignore()
        return True

    # GORSEL SAG TIK KOPYALAMA: BASLANGIC
    def contextMenuEvent(self, event):
        request = self.lastContextMenuRequest()
        if (
            request is not None
            and request.mediaType()
            == QWebEngineContextMenuRequest.MediaType.MediaTypeImage
        ):
            menu = QMenu(self)
            copy_action = menu.addAction("Kopyala")
            copy_action.triggered.connect(
                lambda: self.triggerPageAction(
                    QWebEnginePage.WebAction.CopyImageToClipboard
                )
            )
            menu.exec(event.globalPos())
            return

        super().contextMenuEvent(event)
    # GORSEL SAG TIK KOPYALAMA: BITIS

    def dragEnterEvent(self, event):
        if self._file_paths(event):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._file_paths(event):
            if self._inside_composer_drop_zone(event):
                event.acceptProposedAction()
            else:
                event.ignore()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        file_paths = self._file_paths(event)
        if file_paths:
            if self._inside_composer_drop_zone(event):
                self._on_files_dropped(file_paths[:1])
                event.acceptProposedAction()
            else:
                event.ignore()
            return
        super().dropEvent(event)


class GakkoSohbetPenceresi(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Gakko")
        self.resize(1200, 820)
        self.setMinimumSize(900, 620)

        self.web = AttachmentWebView(self._add_dropped_files, self)
        self.web.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        self.web.setStyleSheet("background:#080b11; border:0;")
        self.web.page().setBackgroundColor(QColor("#080b11"))

        self.bridge = ChatBridge()
        self.records_bridge = KayitlarKoprusu()

        self.channel = QWebChannel(self.web.page())
        self.channel.registerObject("gakkoBridge", self.bridge)
        self.channel.registerObject("kayitlarBridge", self.records_bridge)
        self.web.page().setWebChannel(self.channel)

        index_path = Path(__file__).resolve().parent / "index.html"
        self.web.setUrl(QUrl.fromLocalFile(str(index_path)))

        self.setCentralWidget(self.web)
        self.bridge.start()

    def _add_dropped_files(self, file_paths):
        paths = [str(path) for path in file_paths[:1] if str(path).strip()]
        if not paths:
            return

        self.bridge.add_chat_files(
            json.dumps(paths, ensure_ascii=False)
        )

    def closeEvent(self, event):
        if not self.bridge.close():
            event.ignore()
            return
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gakko")

    window = GakkoSohbetPenceresi()
    window.show()
    _apply_windows_dark_titlebar(window)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
