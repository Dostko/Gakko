from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from ..sohbet_gecmisi import get_history_db_path


SESSION_SEARCH_TOOL_NAME = "session_search"
SESSION_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": SESSION_SEARCH_TOOL_NAME,
        "description": (
            "GAKKO sohbet geçmişinde salt okunur arama yapar. Kullanıcı önceki "
            "konuşmaları, geçen haftayı veya aktif projede en son konuşulanları "
            "sorduğunda kullan. Bir kullanıcı isteğinde en fazla bir kez çağır. "
            "query boş bırakılırsa tarih ve proje kapsamındaki en son konuşmaları getirir."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Aranacak kısa ifade. Yalnız son konuşmalar isteniyorsa boş string kullan."
                    ),
                },
                "scope": {
                    "type": "string",
                    "enum": ["active_project", "all"],
                    "default": "active_project",
                    "description": (
                        "active_project yalnız açık projeyi, all bütün geçmişi arar."
                    ),
                },
                "start_date": {
                    "type": "string",
                    "description": "İsteğe bağlı başlangıç tarihi: YYYY-MM-DD.",
                },
                "end_date": {
                    "type": "string",
                    "description": "İsteğe bağlı bitiş tarihi: YYYY-MM-DD.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 3,
                    "default": 3,
                    "description": "Döndürülecek en fazla oturum sayısı.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


def _normalized_project_path(value):
    return str(value or "").strip().replace("\\", "/").rstrip("/").casefold()


def _date_bounds(arguments):
    start_text = str(arguments.get("start_date") or "").strip()
    end_text = str(arguments.get("end_date") or "").strip()
    start_value = date.fromisoformat(start_text) if start_text else None
    end_value = date.fromisoformat(end_text) if end_text else None

    if start_value and end_value and start_value > end_value:
        raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")

    start_iso = f"{start_value.isoformat()}T00:00:00" if start_value else None
    end_iso = (
        f"{(end_value + timedelta(days=1)).isoformat()}T00:00:00"
        if end_value
        else None
    )
    return start_iso, end_iso


def _message_date_clauses(alias, start_iso, end_iso, params):
    clauses = []
    if start_iso:
        clauses.append(f"{alias}.created_at >= ?")
        params.append(start_iso)
    if end_iso:
        clauses.append(f"{alias}.created_at < ?")
        params.append(end_iso)
    return clauses


def _session_rows(connection, query, project_path, start_iso, end_iso, limit):
    params = []
    dated_message_conditions = ["dm.conversation_id = c.id"]
    dated_message_conditions.extend(
        _message_date_clauses("dm", start_iso, end_iso, params)
    )

    where = [
        "EXISTS (SELECT 1 FROM messages dm WHERE "
        + " AND ".join(dated_message_conditions)
        + ")"
    ]

    if project_path:
        where.append(
            "REPLACE(LOWER(c.project_path), '\\', '/') = ?"
        )
        params.append(project_path)

    if query:
        needle = f"%{query}%"
        query_params = []
        message_conditions = ["qm.conversation_id = c.id"]
        message_conditions.extend(
            _message_date_clauses("qm", start_iso, end_iso, query_params)
        )
        message_conditions.append("qm.content LIKE ? COLLATE NOCASE")
        query_params.append(needle)
        where.append(
            "(c.title LIKE ? COLLATE NOCASE "
            "OR c.project_path LIKE ? COLLATE NOCASE "
            "OR EXISTS (SELECT 1 FROM messages qm WHERE "
            + " AND ".join(message_conditions)
            + "))"
        )
        params.extend([needle, needle, *query_params])

    params.append(limit)
    return connection.execute(
        f"""
        SELECT c.id, c.created_at, c.updated_at, c.title, c.project_path
        FROM conversations c
        WHERE {' AND '.join(where)}
        ORDER BY c.updated_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def _message_rows(connection, session_id, query, start_iso, end_iso):
    date_params = []
    date_clauses = _message_date_clauses(
        "m", start_iso, end_iso, date_params
    )
    base_where = ["m.conversation_id = ?", *date_clauses]
    base_params = [session_id, *date_params]

    matched_ids = []
    if query:
        rows = connection.execute(
            f"""
            SELECT m.id, m.role
            FROM messages m
            WHERE {' AND '.join(base_where)}
              AND m.content LIKE ? COLLATE NOCASE
            ORDER BY m.id DESC
            LIMIT 3
            """,
            [*base_params, f"%{query}%"],
        ).fetchall()
        matched_rows = rows
        matched_ids = [int(row["id"]) for row in matched_rows]

    if not matched_ids:
        return connection.execute(
            f"""
            SELECT m.id, m.role, m.content, m.created_at
            FROM messages m
            WHERE {' AND '.join(base_where)}
            ORDER BY m.id DESC
            LIMIT 4
            """,
            base_params,
        ).fetchall()[::-1]

    selected_ids = set(matched_ids)
    for matched in matched_rows:
        message_id = int(matched["id"])
        if matched["role"] == "user":
            operator = ">"
            aggregate = "MIN"
        else:
            operator = "<"
            aggregate = "MAX"

        neighbor = connection.execute(
            f"""
            SELECT {aggregate}(m.id) AS neighbor_id
            FROM messages m
            WHERE {' AND '.join(base_where)} AND m.id {operator} ?
            """,
            [*base_params, message_id],
        ).fetchone()
        if neighbor["neighbor_id"] is not None:
            selected_ids.add(int(neighbor["neighbor_id"]))

    ordered_ids = sorted(selected_ids)[-6:]
    placeholders = ",".join("?" for _ in ordered_ids)
    return connection.execute(
        f"""
        SELECT id, role, content, created_at
        FROM messages
        WHERE conversation_id = ? AND id IN ({placeholders})
        ORDER BY id ASC
        """,
        [session_id, *ordered_ids],
    ).fetchall()


def _message_payload(row):
    content = str(row["content"] or "")
    truncated = len(content) > 2000
    if truncated:
        content = content[:2000].rstrip() + "…"
    return {
        "role": row["role"],
        "content": content,
        "created_at": row["created_at"],
        "truncated": truncated,
    }


def session_search(arguments, active_project_root=None, db_path=None):
    arguments = arguments if isinstance(arguments, dict) else {}
    query = str(arguments.get("query") or "").strip()
    scope = str(arguments.get("scope") or "active_project").strip()

    if scope not in {"active_project", "all"}:
        return "[GEÇMİŞ ARAMA HATASI] Geçersiz arama kapsamı."

    project_path = ""
    if scope == "active_project":
        project_path = _normalized_project_path(active_project_root)
        if not project_path:
            return "[GEÇMİŞ ARAMA HATASI] Aktif proje bulunmuyor."

    try:
        limit = min(3, max(1, int(arguments.get("limit", 3))))
        start_iso, end_iso = _date_bounds(arguments)
    except (TypeError, ValueError) as error:
        return f"[GEÇMİŞ ARAMA HATASI] {error}"

    database_path = Path(db_path or get_history_db_path()).resolve()
    if not database_path.is_file():
        return "[GEÇMİŞ ARAMA HATASI] Sohbet geçmişi veritabanı bulunamadı."

    try:
        database_uri = database_path.as_uri() + "?mode=ro"
        with sqlite3.connect(database_uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            sessions = _session_rows(
                connection,
                query,
                project_path,
                start_iso,
                end_iso,
                limit,
            )
            results = []
            for session in sessions:
                messages = _message_rows(
                    connection,
                    session["id"],
                    query,
                    start_iso,
                    end_iso,
                )
                results.append(
                    {
                        "session_id": session["id"],
                        "title": session["title"],
                        "project_path": session["project_path"],
                        "created_at": session["created_at"],
                        "updated_at": session["updated_at"],
                        "messages": [_message_payload(row) for row in messages],
                    }
                )
    except sqlite3.Error as error:
        return f"[GEÇMİŞ ARAMA HATASI] SQLite araması başarısız: {error}"

    return json.dumps(
        {
            "query": query,
            "scope": scope,
            "result_count": len(results),
            "results": results,
        },
        ensure_ascii=False,
    )
