import json
import sqlite3

from Sohbet_Bilesenleri.sohbet_gecmisi import HISTORY_RETENTION_DAYS


class SohbetGecmisiKoprusu:
    def __init__(self, bridge):
        self.bridge = bridge

    def ensure_session(self):
        bridge = self.bridge
        if bridge.history_session_id is None:
            project_path = (
                str(bridge.active_project_root)
                if bridge.active_project_root is not None
                else ""
            )
            bridge.history_session_id = bridge.history.create_session(project_path)
        return bridge.history_session_id

    def list_history(self, query=""):
        bridge = self.bridge
        try:
            payload = {
                "retention_days": HISTORY_RETENTION_DAYS,
                "sessions": bridge.history.list_sessions(query),
            }
            bridge.history_sessions_ready.emit(
                json.dumps(payload, ensure_ascii=False)
            )
        except Exception as error:
            bridge.error_ready.emit(f"Sohbet geçmişi okunamadı: {error}")

    def get_history_session(self, session_id):
        bridge = self.bridge
        try:
            payload = bridge.history.get_session(session_id) or {}
            bridge.history_session_ready.emit(
                json.dumps(payload, ensure_ascii=False)
            )
        except Exception as error:
            bridge.error_ready.emit(f"Sohbet geçmişi açılamadı: {error}")

    def delete_history_session(self, session_id):
        bridge = self.bridge
        try:
            deleted = bridge.history.delete_session(session_id)
            if deleted and str(session_id) == str(bridge.history_session_id or ""):
                bridge.history_session_id = None
                bridge._history_capture_reply = False
            bridge.history_action_ready.emit(
                json.dumps(
                    {
                        "action": "delete_session",
                        "deleted": 1 if deleted else 0,
                    },
                    ensure_ascii=False,
                )
            )
            self.list_history("")
        except Exception as error:
            bridge.error_ready.emit(f"Sohbet geçmişi silinemedi: {error}")

    def delete_history_before(self, cutoff_iso):
        bridge = self.bridge
        try:
            deleted = bridge.history.delete_before(cutoff_iso)
            if (
                bridge.history_session_id is not None
                and bridge.history.get_session(bridge.history_session_id) is None
            ):
                bridge.history_session_id = None
                bridge._history_capture_reply = False
            bridge.history_action_ready.emit(
                json.dumps(
                    {
                        "action": "delete_before",
                        "deleted": deleted,
                    },
                    ensure_ascii=False,
                )
            )
            self.list_history("")
        except (OSError, ValueError, sqlite3.Error) as error:
            bridge.error_ready.emit(f"Sohbet geçmişi silinemedi: {error}")
