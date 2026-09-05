import json
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView

from Sohbet_Bilesenleri.sohbet_koprusu import ChatBridge


DROP_IMAGE_EXTENSIONS = frozenset({
    ".bmp",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".tif",
    ".tiff",
    ".webp",
})


class AttachmentWebView(QWebEngineView):
    DROP_ZONE_HEIGHT = 240

    def __init__(self, on_images_dropped, parent=None):
        super().__init__(parent)
        self._on_images_dropped = on_images_dropped
        self.setAcceptDrops(True)
        self.loadFinished.connect(self._install_drop_event_filter)

    @staticmethod
    def _image_paths(event):
        mime_data = event.mimeData()
        if mime_data is None or not mime_data.hasUrls():
            return []

        image_paths = []
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue

            path = Path(url.toLocalFile())
            if not path.is_file() or path.suffix.lower() not in DROP_IMAGE_EXTENSIONS:
                continue

            image_paths.append(str(path))

        return image_paths

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

        image_paths = self._image_paths(event)
        if not image_paths:
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
            self._on_images_dropped(image_paths[:1])
            event.acceptProposedAction()
        else:
            event.ignore()
        return True

    def dragEnterEvent(self, event):
        if self._image_paths(event):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._image_paths(event):
            if self._inside_composer_drop_zone(event):
                event.acceptProposedAction()
            else:
                event.ignore()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        image_paths = self._image_paths(event)
        if image_paths:
            if self._inside_composer_drop_zone(event):
                self._on_images_dropped(image_paths[:1])
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

        self.web = AttachmentWebView(self._add_dropped_images, self)
        self.web.setStyleSheet("background:#080b11; border:0;")
        self.web.page().setBackgroundColor(QColor("#080b11"))

        self.bridge = ChatBridge()

        self.channel = QWebChannel(self.web.page())
        self.channel.registerObject("gakkoBridge", self.bridge)
        self.web.page().setWebChannel(self.channel)

        index_path = Path(__file__).resolve().parent / "index.html"
        self.web.setUrl(QUrl.fromLocalFile(str(index_path)))

        self.setCentralWidget(self.web)
        self.bridge.start()

    def _add_dropped_images(self, image_paths):
        paths = [str(path) for path in image_paths[:1] if str(path).strip()]
        if not paths:
            return

        self.bridge.add_chat_files(
            json.dumps(paths, ensure_ascii=False)
        )

    def closeEvent(self, event):
        self.bridge.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gakko")

    window = GakkoSohbetPenceresi()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
