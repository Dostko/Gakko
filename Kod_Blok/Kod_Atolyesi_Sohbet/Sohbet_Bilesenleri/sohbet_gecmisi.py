import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


HISTORY_RETENTION_DAYS = 30
DEFAULT_MEMORY_ROOT = Path(r"D:\Gakko\GAKKO_YUVA\Hafiza")


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
    def __init__(
        self,
        db_path,
        retention_days=HISTORY_RETENTION_DAYS,
        memory_root=None,
    ):
        self.db_path = Path(db_path)
        self.jsonl_path = self.db_path.with_suffix(".jsonl")
        self.memory_root = Path(memory_root or DEFAULT_MEMORY_ROOT)
        self.near_history_root = self.memory_root / "Yakin_Gecmis"
        self.near_history_index = self.memory_root / "Yakin_Gecmis_Fihristi.md"
        self.retention_days = max(1, int(retention_days))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self.cleanup_expired()
        if self._write_jsonl_snapshot():
            self._sync_near_history_md()

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

    @staticmethod
    def _timestamp_parts(timestamp):
        raw_timestamp = str(timestamp or "").strip()
        try:
            parsed = datetime.fromisoformat(
                raw_timestamp.replace("Z", "+00:00")
            )
        except ValueError:
            return "", "", ""

        utc_offset = parsed.utcoffset()
        if utc_offset is None:
            timezone_name = ""
        elif utc_offset == timedelta(0):
            timezone_name = "UTC"
        else:
            total_minutes = int(utc_offset.total_seconds() // 60)
            sign = "+" if total_minutes >= 0 else "-"
            total_minutes = abs(total_minutes)
            hours, minutes = divmod(total_minutes, 60)
            timezone_name = f"UTC{sign}{hours:02d}:{minutes:02d}"

        return (
            parsed.date().isoformat(),
            parsed.time().replace(tzinfo=None).isoformat(timespec="seconds"),
            timezone_name,
        )

    def _replace_jsonl(self, temp_path):
        retry_delays = (0.0, 0.05, 0.10, 0.20)
        for attempt, delay in enumerate(retry_delays):
            if delay:
                time.sleep(delay)
            try:
                temp_path.replace(self.jsonl_path)
                return
            except OSError:
                if attempt == len(retry_delays) - 1:
                    raise

    def _jsonl_record(self, row):
        date, message_time, timezone_name = self._timestamp_parts(
            row["created_at"]
        )
        return {
            "session_id": row["session_id"],
            "session_created_at": row["session_created_at"],
            "session_updated_at": row["session_updated_at"],
            "session_title": row["session_title"],
            "project_path": row["project_path"],
            "project_name": self._project_name(row["project_path"]),
            "message_id": int(row["message_id"]),
            "role": row["role"],
            "created_at": row["created_at"],
            "date": date,
            "time": message_time,
            "timezone": timezone_name,
            "content": row["content"],
        }

    def _last_jsonl_message_id(self):
        if not self.jsonl_path.exists():
            return None

        try:
            with self.jsonl_path.open("rb") as source:
                source.seek(0, os.SEEK_END)
                position = source.tell()
                if position == 0:
                    return 0

                buffer = b""
                while position > 0:
                    chunk_size = min(8192, position)
                    position -= chunk_size
                    source.seek(position)
                    buffer = source.read(chunk_size) + buffer
                    lines = buffer.split(b"\n")
                    complete_lines = lines if position == 0 else lines[1:]

                    for line in reversed(complete_lines):
                        if line.strip():
                            record = json.loads(line.decode("utf-8"))
                            return int(record["message_id"])
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError):
            return None

        return 0

    def _append_missing_jsonl_messages(self):
        rebuild_required = False
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                last_message_id = self._last_jsonl_message_id()
                if last_message_id is None:
                    rebuild_required = True
                else:
                    rows = connection.execute(
                        """
                        SELECT
                            c.id AS session_id,
                            c.created_at AS session_created_at,
                            m.created_at AS session_updated_at,
                            CASE
                                WHEN EXISTS (
                                    SELECT 1
                                    FROM messages first_user
                                    WHERE first_user.conversation_id = c.id
                                      AND first_user.role = 'user'
                                      AND first_user.id <= m.id
                                ) THEN c.title
                                ELSE 'Yeni sohbet'
                            END AS session_title,
                            c.project_path,
                            m.id AS message_id,
                            m.role,
                            m.content,
                            m.created_at
                        FROM messages m
                        JOIN conversations c ON c.id = m.conversation_id
                        WHERE m.id > ?
                        ORDER BY m.id ASC
                        """,
                        (last_message_id,),
                    )
                    with self.jsonl_path.open(
                        "a", encoding="utf-8", newline="\n"
                    ) as output:
                        for row in rows:
                            output.write(
                                json.dumps(
                                    self._jsonl_record(row),
                                    ensure_ascii=False,
                                )
                                + "\n"
                            )
        except (OSError, sqlite3.Error, ValueError):
            return False

        if rebuild_required:
            return self._write_jsonl_snapshot()
        return True

    def _publish_jsonl_snapshot(self, connection):
        temp_path = self.jsonl_path.with_name(
            f".{self.jsonl_path.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            rows = connection.execute(
                """
                SELECT
                    c.id AS session_id,
                    c.created_at AS session_created_at,
                    m.created_at AS session_updated_at,
                    CASE
                        WHEN EXISTS (
                            SELECT 1
                            FROM messages first_user
                            WHERE first_user.conversation_id = c.id
                              AND first_user.role = 'user'
                              AND first_user.id <= m.id
                        ) THEN c.title
                        ELSE 'Yeni sohbet'
                    END AS session_title,
                    c.project_path,
                    m.id AS message_id,
                    m.role,
                    m.content,
                    m.created_at
                FROM conversations c
                JOIN messages m ON m.conversation_id = c.id
                ORDER BY m.id ASC
                """
            )

            with temp_path.open("w", encoding="utf-8", newline="\n") as output:
                for row in rows:
                    output.write(
                        json.dumps(
                            self._jsonl_record(row),
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

            self._replace_jsonl(temp_path)
        except (OSError, sqlite3.Error, ValueError):
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return False

        return True

    def _write_jsonl_snapshot(self):
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                return self._publish_jsonl_snapshot(connection)
        except sqlite3.Error:
            return False

    @staticmethod
    def _session_md_filename(records):
        first_record = records[0]
        date = str(first_record.get("date") or "tarihsiz")
        message_time = str(first_record.get("time") or "saatsiz").replace(":", "-")
        session_id = str(first_record.get("session_id") or "oturum")[:8]
        return f"{date}_{message_time}_{session_id}.md"

    @staticmethod
    def _render_session_md(records):
        first_record = records[0]
        lines = [
            "# YAKIN SOHBET GECMISI",
            "",
            f"Oturum: {first_record.get('session_id', '')}",
            (
                "Baslangic: "
                f"{first_record.get('date', '')} "
                f"{first_record.get('time', '')} "
                f"{first_record.get('timezone', '')}"
            ).rstrip(),
            f"Proje: {first_record.get('project_path', '') or '-'}",
            "",
            "## Mesajlar",
            "",
        ]

        for record in records:
            role = "Kullanici" if record.get("role") == "user" else "Qwen"
            lines.extend(
                [
                    (
                        f"### {record.get('date', '')} "
                        f"{record.get('time', '')} — {role}"
                    ),
                    "",
                    str(record.get("content") or ""),
                    "",
                ]
            )

        return "\n".join(lines).rstrip() + "\n"

    def _sync_near_history_md(self):
        try:
            sessions = {}
            with self.jsonl_path.open("r", encoding="utf-8") as source:
                for line in source:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    session_id = str(record.get("session_id") or "").strip()
                    if session_id:
                        sessions.setdefault(session_id, []).append(record)

            self.near_history_root.mkdir(parents=True, exist_ok=True)
            active_files = set()
            index_entries = []

            for records in sessions.values():
                records.sort(key=lambda item: int(item.get("message_id") or 0))
                filename = self._session_md_filename(records)
                active_files.add(filename)
                session_path = self.near_history_root / filename
                session_path.write_text(
                    self._render_session_md(records),
                    encoding="utf-8",
                )

                first_record = records[0]
                last_record = records[-1]
                user_message_starts = []
                for record in records:
                    if record.get("role") != "user":
                        continue
                    message_start = " ".join(
                        str(record.get("content") or "").split()
                    )
                    if not message_start:
                        continue
                    if len(message_start) > 80:
                        message_start = message_start[:77].rstrip() + "..."
                    user_message_starts.append(message_start)

                index_entries.append(
                    {
                        "sort_key": int(last_record.get("message_id") or 0),
                        "date": first_record.get("date", ""),
                        "time": first_record.get("time", ""),
                        "title": first_record.get("session_title", "Yeni sohbet"),
                        "project": first_record.get("project_path", "") or "-",
                        "user_message_starts": user_message_starts[-2:],
                        "filename": filename,
                    }
                )

            for existing_path in self.near_history_root.glob("*.md"):
                if existing_path.name not in active_files:
                    existing_path.unlink()

            index_entries.sort(key=lambda item: item["sort_key"], reverse=True)
            index_entries = index_entries[:50]
            index_lines = [
                "# YAKIN GECMIS FIHRISTI",
                "",
                "JSONL sohbet geçmişinden mekanik olarak üretilir.",
                "İçerik özetlenmez, yorumlanmaz veya önem sırasına konulmaz.",
                "",
                "## Oturumlar",
                "",
            ]

            if index_entries:
                for entry in index_entries:
                    index_lines.extend(
                        [
                            (
                                f"- {entry['date']} {entry['time']} — "
                                f"{entry['title']}"
                            ),
                            f"  Proje: {entry['project']}",
                        ]
                    )
                    if entry["user_message_starts"]:
                        index_lines.append("  Gerçek kullanıcı mesajları:")
                        for message_start in entry["user_message_starts"]:
                            index_lines.append(f"    - {message_start}")
                    index_lines.append(
                        "  Kaynak: `GAKKO_YUVA/Hafiza/Yakin_Gecmis/"
                        f"{entry['filename']}`"
                    )
            else:
                index_lines.append("Henüz yakın sohbet geçmişi yok.")

            self.near_history_index.write_text(
                "\n".join(index_lines).rstrip() + "\n",
                encoding="utf-8",
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return False

        return True

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
        if self._append_missing_jsonl_messages():
            self._sync_near_history_md()
        return True

    def cleanup_expired(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "DELETE FROM conversations WHERE updated_at < ?",
                (cutoff.isoformat(timespec="seconds"),),
            )
            deleted = max(0, int(cursor.rowcount or 0))

            if deleted and not self._publish_jsonl_snapshot(connection):
                connection.rollback()
                return 0

        if deleted:
            self._sync_near_history_md()
        return deleted

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
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (session_id,),
            )
            deleted = int(cursor.rowcount or 0) > 0

            if deleted and not self._publish_jsonl_snapshot(connection):
                connection.rollback()
                return False

        if deleted:
            self._sync_near_history_md()
        return deleted

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
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "DELETE FROM conversations WHERE updated_at < ?",
                (cutoff.isoformat(timespec="seconds"),),
            )
            deleted = max(0, int(cursor.rowcount or 0))

            if deleted and not self._publish_jsonl_snapshot(connection):
                connection.rollback()
                return 0

        if deleted:
            self._sync_near_history_md()
        return deleted
