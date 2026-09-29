"""SQLite persistence for the support-tickets MVP."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

DB_PATH = Path(os.getenv("SUPPORT_TICKETS_DB", "support_tickets.db"))
STATUSES = ("Open", "In progress", "Waiting on customer", "Resolved", "Closed")
PRIORITIES = ("Low", "Medium", "High", "Urgent")


@contextmanager
def _connection(db_path: str | Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db(db_path: str | Path = DB_PATH) -> None:
    """Create the ticket and comment tables if they do not already exist."""
    with _connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                requester TEXT NOT NULL DEFAULT '',
                requester_email TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'Open',
                assigned_to TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                author TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
            CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);
            CREATE INDEX IF NOT EXISTS idx_comments_ticket_id ON comments(ticket_id);
            """
        )


def create_ticket(
    title: str,
    description: str,
    requester: str = "",
    requester_email: str = "",
    priority: str = "Medium",
    assigned_to: str = "",
    db_path: str | Path = DB_PATH,
) -> int:
    """Create a ticket and return its numeric ID."""
    title = title.strip()
    description = description.strip()
    if not title:
        raise ValueError("Ticket title is required.")
    if not description:
        raise ValueError("Ticket description is required.")
    if priority not in PRIORITIES:
        raise ValueError(f"Priority must be one of: {', '.join(PRIORITIES)}.")

    now = _now()
    with _connection(db_path) as connection:
        cursor = connection.execute(
            """INSERT INTO tickets
               (title, description, requester, requester_email, priority,
                status, assigned_to, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?)""",
            (
                title,
                description,
                requester.strip(),
                requester_email.strip(),
                priority,
                assigned_to.strip(),
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)


def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    search: str = "",
    db_path: str | Path = DB_PATH,
) -> list[dict[str, object]]:
    """List tickets with optional status, priority, and text filters."""
    if status is not None and status not in STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(STATUSES)}.")
    if priority is not None and priority not in PRIORITIES:
        raise ValueError(f"Priority must be one of: {', '.join(PRIORITIES)}.")

    clauses: list[str] = []
    values: list[object] = []
    if status:
        clauses.append("status = ?")
        values.append(status)
    if priority:
        clauses.append("priority = ?")
        values.append(priority)
    term = search.strip().lower()
    if term:
        clauses.append(
            "(lower(title) LIKE ? OR lower(description) LIKE ? "
            "OR lower(requester) LIKE ? OR lower(requester_email) LIKE ? "
            "OR lower(assigned_to) LIKE ?)"
        )
        pattern = f"%{term}%"
        values.extend([pattern] * 5)

    query = "SELECT * FROM tickets"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC"
    with _connection(db_path) as connection:
        return [dict(row) for row in connection.execute(query, values).fetchall()]


def get_ticket(ticket_id: int, db_path: str | Path = DB_PATH) -> dict[str, object] | None:
    with _connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return dict(row) if row else None


def update_ticket(
    ticket_id: int,
    status: str,
    priority: str,
    assigned_to: str = "",
    db_path: str | Path = DB_PATH,
) -> bool:
    """Update a ticket's status, priority, and assignee; return whether it exists."""
    if status not in STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(STATUSES)}.")
    if priority not in PRIORITIES:
        raise ValueError(f"Priority must be one of: {', '.join(PRIORITIES)}.")
    with _connection(db_path) as connection:
        cursor = connection.execute(
            """UPDATE tickets
               SET status = ?, priority = ?, assigned_to = ?, updated_at = ?
               WHERE id = ?""",
            (status, priority, assigned_to.strip(), _now(), ticket_id),
        )
        return cursor.rowcount > 0


def add_comment(
    ticket_id: int,
    author: str,
    body: str,
    db_path: str | Path = DB_PATH,
) -> int:
    """Add an internal note to a ticket and return the note ID."""
    author = author.strip()
    body = body.strip()
    if not author:
        raise ValueError("Comment author is required.")
    if not body:
        raise ValueError("Comment text is required.")
    with _connection(db_path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if not exists:
            raise ValueError(f"Ticket {ticket_id} does not exist.")
        cursor = connection.execute(
            "INSERT INTO comments (ticket_id, author, body, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, author, body, _now()),
        )
        connection.execute(
            "UPDATE tickets SET updated_at = ? WHERE id = ?", (_now(), ticket_id)
        )
        return int(cursor.lastrowid)


def list_comments(ticket_id: int, db_path: str | Path = DB_PATH) -> list[dict[str, object]]:
    with _connection(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM comments WHERE ticket_id = ? ORDER BY id ASC", (ticket_id,)
        ).fetchall()
        return [dict(row) for row in rows]
