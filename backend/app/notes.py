"""Note storage in PostgreSQL: plain, parameterised SQL through a psycopg connection pool.

`NoteStore` is the only module that talks to the database. Routes depend on the `Notes` protocol,
so tests can swap in an in-memory fake without touching SQL.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import psycopg
from psycopg.rows import class_row
from psycopg_pool import ConnectionPool

from app.errors import DatabaseUnavailableError


@dataclass
class Note:
    id: int
    title: str
    body: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ScoredNote(Note):
    score: float


class Notes(Protocol):
    def ping(self) -> None: ...
    def page(self, limit: int, offset: int) -> tuple[list[Note], int]: ...
    def get(self, note_id: int) -> Note | None: ...
    def create(self, title: str, body: str) -> Note: ...
    def update(self, note_id: int, title: str | None, body: str | None) -> Note | None: ...
    def delete(self, note_id: int) -> bool: ...
    def search(self, text: str, limit: int) -> list[ScoredNote]: ...
    def recent(self, limit: int) -> list[Note]: ...


# Retrieval. plainto_tsquery() turns free text into lexemes joined by AND ('deploy' & 'server').
# A question rarely contains every word of the note it is about, so the AND becomes OR, and
# ts_rank_cd() puts the notes that match more (and in the title, weight A) first.
_SEARCH_SQL = """
WITH q AS (
    SELECT replace(plainto_tsquery('english', %(text)s)::text, ' & ', ' | ')::tsquery AS query
)
SELECT n.id, n.title, n.body, n.created_at, n.updated_at,
       ts_rank_cd(n.search, q.query) AS score
FROM notes AS n
CROSS JOIN q
WHERE n.search @@ q.query
ORDER BY score DESC, n.updated_at DESC
LIMIT %(limit)s
"""


class NoteStore:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def _conn(self):
        try:
            return self.pool.connection()
        except psycopg.OperationalError as exc:  # pragma: no cover - exercised against a live DB
            raise DatabaseUnavailableError(
                "PostgreSQL is not reachable.",
                hint="Check `docker compose ps postgres` and `docker compose logs postgres`.",
            ) from exc

    def ping(self) -> None:
        with self._conn() as conn:
            # Probe the work path, not just the socket: the notes table must exist.
            conn.execute("SELECT 1 FROM notes LIMIT 1")

    def page(self, limit: int, offset: int) -> tuple[list[Note], int]:
        with self._conn() as conn:
            total = conn.execute("SELECT count(*) FROM notes").fetchone()[0]
            cur = conn.cursor(row_factory=class_row(Note))
            rows = cur.execute(
                "SELECT id, title, body, created_at, updated_at FROM notes "
                "ORDER BY updated_at DESC, id DESC LIMIT %s OFFSET %s",
                (limit, offset),
            ).fetchall()
        return rows, total

    def get(self, note_id: int) -> Note | None:
        with self._conn() as conn:
            cur = conn.cursor(row_factory=class_row(Note))
            return cur.execute(
                "SELECT id, title, body, created_at, updated_at FROM notes WHERE id = %s",
                (note_id,),
            ).fetchone()

    def create(self, title: str, body: str) -> Note:
        with self._conn() as conn:
            cur = conn.cursor(row_factory=class_row(Note))
            return cur.execute(
                "INSERT INTO notes (title, body) VALUES (%s, %s) "
                "RETURNING id, title, body, created_at, updated_at",
                (title, body),
            ).fetchone()

    def update(self, note_id: int, title: str | None, body: str | None) -> Note | None:
        with self._conn() as conn:
            cur = conn.cursor(row_factory=class_row(Note))
            return cur.execute(
                """
                UPDATE notes
                SET title = COALESCE(%(title)s, title),
                    body = COALESCE(%(body)s, body),
                    updated_at = now()
                WHERE id = %(id)s
                RETURNING id, title, body, created_at, updated_at
                """,
                {"id": note_id, "title": title, "body": body},
            ).fetchone()

    def delete(self, note_id: int) -> bool:
        with self._conn() as conn:
            return conn.execute("DELETE FROM notes WHERE id = %s", (note_id,)).rowcount == 1

    def search(self, text: str, limit: int) -> list[ScoredNote]:
        with self._conn() as conn:
            cur = conn.cursor(row_factory=class_row(ScoredNote))
            return cur.execute(_SEARCH_SQL, {"text": text, "limit": limit}).fetchall()

    def recent(self, limit: int) -> list[Note]:
        with self._conn() as conn:
            cur = conn.cursor(row_factory=class_row(Note))
            return cur.execute(
                "SELECT id, title, body, created_at, updated_at FROM notes "
                "ORDER BY updated_at DESC, id DESC LIMIT %s",
                (limit,),
            ).fetchall()
