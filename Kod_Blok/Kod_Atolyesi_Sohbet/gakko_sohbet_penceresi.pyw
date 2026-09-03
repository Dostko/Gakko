import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView

from Sohbet_Bilesenleri.sohbet_koprusu import ChatBridge


class GakkoSohbetPenceresi(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Gakko")
        self.resize(1200, 820)
        self.setMinimumSize(900, 620)

        self.web = QWebEngineView(self)
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
