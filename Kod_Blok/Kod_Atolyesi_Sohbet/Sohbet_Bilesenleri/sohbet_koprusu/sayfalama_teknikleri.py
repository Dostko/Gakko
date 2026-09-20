import json


class SayfalamaTeknikleri:
    SETTINGS_KEY = "active_chat_session_id"

    def __init__(self, bridge):
        self.bridge = bridge

    @staticmethod
    def _empty_payload():
        return {"id": "", "messages": []}

    def _emit_page(self, payload):
        self.bridge.active_chat_ready.emit(
            json.dumps(payload, ensure_ascii=False)
        )

    def _save_active_id(self, session_id):
        self.bridge.settings.setValue(
            self.SETTINGS_KEY,
            str(session_id or ""),
        )
        self.bridge.settings.sync()

    def remember_active_session(self, session_id):
        session_id = str(session_id or "").strip()
        if not session_id:
            return False

        self._save_active_id(session_id)
        return True

    def _saved_session_id(self):
        settings = self.bridge.settings

        if settings.contains(self.SETTINGS_KEY):
            return str(settings.value(self.SETTINGS_KEY, "") or "").strip()

        sessions = self.bridge.history.list_sessions("")
        if not sessions:
            self._save_active_id("")
            return ""

        session_id = str(sessions[0].get("id") or "").strip()
        self._save_active_id(session_id)
        return session_id

    def load_active_page(self):
        bridge = self.bridge
        session_id = self._saved_session_id()

        if not session_id:
            bridge.history_session_id = None
            bridge._history_capture_reply = False
            bridge.session.restore_history([])
            self._emit_page(self._empty_payload())
            return True

        session = bridge.history.get_session(session_id)
        if not session:
            bridge.history_session_id = None
            bridge._history_capture_reply = False
            bridge.session.restore_history([])
            self._save_active_id("")
            self._emit_page(self._empty_payload())
            return True

        messages = session.get("messages")
        if not isinstance(messages, list):
            messages = []

        bridge.history_session_id = session_id
        bridge._history_capture_reply = False
        bridge.session.restore_history(messages)
        self._emit_page(session)
        return True

    def start_new_page(self):
        bridge = self.bridge

        if bridge._busy:
            bridge.error_ready.emit(
                "GAKKO şu anda başka bir mesaja cevap veriyor."
            )
            return False

        if not bridge.session.reset_context():
            return False

        bridge.history_session_id = None
        bridge._history_capture_reply = False
        self._save_active_id("")
        self._emit_page(self._empty_payload())
        return True
