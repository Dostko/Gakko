import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout


BASE_DIR = Path(__file__).resolve().parent
CHAT_FILE = BASE_DIR / "Kod_Atolyesi_Sohbet" / "gakko_sohbet_penceresi.pyw"


class GakkoGUI(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Gakko")
        self.resize(320, 160)

        self.chat_button = QPushButton("GAKKO SOHBET")
        self.chat_button.setMinimumHeight(50)
        self.chat_button.clicked.connect(self.open_chat)

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.addWidget(self.chat_button)

        self.setLayout(layout)

    def open_chat(self):
        if not CHAT_FILE.exists():
            self.chat_button.setText("Sohbet dosyası bulunamadı")
            return

        subprocess.Popen(
            [sys.executable, str(CHAT_FILE)],
            cwd=str(CHAT_FILE.parent),
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = GakkoGUI()
    window.show()

    sys.exit(app.exec())
