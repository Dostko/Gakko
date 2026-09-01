import sys
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView


class ChatBridge(QObject):
    reply_ready = Signal(str)
    error_ready = Signal(str)
    connection_ready = Signal()

    @Slot(str)
    def send_message(self, message):
        print(f"JS'den gelen mesaj: {message}")
        self.reply_ready.emit(f"Test cevabı: {message}")


def main():
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Bridge Test")
    window.resize(1200, 820)

    web = QWebEngineView(window)
    bridge = ChatBridge()

    channel = QWebChannel(web.page())
    channel.registerObject("gakkoBridge", bridge)
    web.page().setWebChannel(channel)

    index_path = Path(r"D:\Gakko\Kod_Blok\Kod_Atolyesi_Sohbet\index.html")
    web.setUrl(QUrl.fromLocalFile(str(index_path)))

    window.setCentralWidget(web)
    window.show()

    bridge.connection_ready.emit()

    print("Pencere açıldı.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()