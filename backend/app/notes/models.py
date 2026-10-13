"""The note domain: what a note is, and what any note store must offer.

Routes and the assistant depend on the `Notes` protocol, not on PostgreSQL, so tests can swap in
an in-memory fake without touching SQL.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


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
