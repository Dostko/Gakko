import sys
from pathlib import Path

from Terminal.terminal_penceresi import run_terminal_launcher


BASE_DIR = Path(__file__).resolve().parent
CHAT_FILE = BASE_DIR / "Kod_Atolyesi_Sohbet" / "gakko_sohbet_penceresi.pyw"


if __name__ == "__main__":
    sys.exit(run_terminal_launcher(CHAT_FILE))
