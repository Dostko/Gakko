from PySide6.QtWidgets import QApplication


class EkranGorunum:
    def copy_text_to_clipboard(self, text):
        value = str(text or "")
        if not value:
            return False

        application = QApplication.instance()
        if application is None:
            return False

        clipboard = application.clipboard()
        if clipboard is None:
            return False

        clipboard.setText(value)
        return True
