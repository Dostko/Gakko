import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


HISTORY_RETENTION_DAYS = 30


def get_history_db_path():
    local_app_data = str(os.environ.get("LOCALAPPDATA") or "").strip()
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / ".local" / "share"

    history_dir = base / "Gakko"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / "history.sqlite3"


class ChatHistoryStore:
    def __init__(self, db_path, retention_days=HISTORY_RETENTION_DAYS):
        self.db_path = Path(db_path)
        self.retention_days = max(1, int(retention_days))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self.cleanup_expired()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT 'Yeni sohbet',
                    project_path TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_history_updated_at
                    ON conversations(updated_at);

                CREATE INDEX IF NOT EXISTS idx_history_messages_conversation
                    ON messages(conversation_id, id);
                """
            )

    @staticmethod
    def _now_iso():
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _project_name(project_path):
        clean = str(project_path or "").strip().rstrip("\\/")
        if not clean:
            return ""
        return clean.replace("\\", "/").rsplit("/", 1)[-1]

    @staticmethod
    def _title_from_message(message):
        clean = " ".join(str(message or "").split())
        if not clean:
            return "Yeni sohbet"
        if len(clean) <= 72:
            return clean
        return clean[:69].rstrip() + "..."

    def create_session(self, project_path=""):
        session_id = str(uuid.uuid4())
        now = self._now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (
                    id, created_at, updated_at, title, project_path
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, now, now, "Yeni sohbet", str(project_path or "")),
            )
        return session_id

    def add_message(self, session_id, role, content):
        session_id = str(session_id or "").strip()
        role = str(role or "").strip().lower()
        content = str(content or "").strip()

        if not session_id or role not in {"user", "assistant"} or not content:
            return False

        now = self._now_iso()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT title FROM conversations WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return False

            connection.execute(
                """
                INSERT INTO messages (
                    conversation_id, role, content, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, now),
            )

            title = row["title"]
            if role == "user" and title == "Yeni sohbet":
                title = self._title_from_message(content)

            connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?, title = ?
                WHERE id = ?
                """,
                (now, title, session_id),
            )
        return True

    def cleanup_expired(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE updated_at < ?",
                (cutoff.isoformat(timespec="seconds"),),
            )
            return max(0, int(cursor.rowcount or 0))

    def list_sessions(self, query=""):
        self.cleanup_expired()
        query = str(query or "").strip()
        params = []
        where = ""

        if query:
            needle = f"%{query}%"
            where = """
                WHERE c.title LIKE ? COLLATE NOCASE
                   OR c.project_path LIKE ? COLLATE NOCASE
                   OR EXISTS (
                       SELECT 1
                       FROM messages sm
                       WHERE sm.conversation_id = c.id
                         AND sm.content LIKE ? COLLATE NOCASE
                   )
            """
            params.extend([needle, needle, needle])

        sql = f"""
            SELECT
                c.id,
                c.created_at,
                c.updated_at,
                c.title,
                c.project_path,
                COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            {where}
            GROUP BY c.id
            HAVING COUNT(m.id) > 0
            ORDER BY c.updated_at DESC
        """

        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        return [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "title": row["title"],
                "project_path": row["project_path"],
                "project_name": self._project_name(row["project_path"]),
                "message_count": int(row["message_count"] or 0),
            }
            for row in rows
        ]

    def get_session(self, session_id):
        session_id = str(session_id or "").strip()
        if not session_id:
            return None

        with self._connect() as connection:
            conversation = connection.execute(
                """
                SELECT id, created_at, updated_at, title, project_path
                FROM conversations
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()

            if conversation is None:
                return None

            messages = connection.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()

        return {
            "id": conversation["id"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
            "title": conversation["title"],
            "project_path": conversation["project_path"],
            "project_name": self._project_name(conversation["project_path"]),
            "messages": [
                {
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                }
                for row in messages
            ],
        }

    def delete_session(self, session_id):
        session_id = str(session_id or "").strip()
        if not session_id:
            return False

        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (session_id,),
            )
            return int(cursor.rowcount or 0) > 0

    def delete_before(self, cutoff_iso):
        cutoff_text = str(cutoff_iso or "").strip()
        if not cutoff_text:
            return 0

        try:
            cutoff = datetime.fromisoformat(cutoff_text.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("Geçerli bir tarih seçilmedi.") from error

        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        cutoff = cutoff.astimezone(timezone.utc)

        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE updated_at < ?",
                (cutoff.isoformat(timespec="seconds"),),
            )
            return max(0, int(cursor.rowcount or 0))
