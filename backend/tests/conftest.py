"""Fakes for the two boundaries (PostgreSQL and Ollama) so the real routes run without Docker."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.errors import LLMUnavailableError
from app.llm import ChatResult, ModelInfo
from app.main import create_app
from app.notes import Note, ScoredNote

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


class FakeNotes:
    def __init__(self):
        self.rows: dict[int, Note] = {}
        self.next_id = 1
        self.clock = 0

    def _now(self) -> datetime:
        self.clock += 1
        return BASE_TIME + timedelta(seconds=self.clock)

    def ping(self) -> None:
        return None

    def page(self, limit, offset):
        ordered = sorted(self.rows.values(), key=lambda n: (n.updated_at, n.id), reverse=True)
        return ordered[offset : offset + limit], len(ordered)

    def get(self, note_id):
        return self.rows.get(note_id)

    def create(self, title, body):
        now = self._now()
        note = Note(self.next_id, title, body, now, now)
        self.rows[note.id] = note
        self.next_id += 1
        return note

    def update(self, note_id, title, body):
        note = self.rows.get(note_id)
        if note is None:
            return None
        note.title = title if title is not None else note.title
        note.body = body if body is not None else note.body
        note.updated_at = self._now()
        return note

    def delete(self, note_id):
        return self.rows.pop(note_id, None) is not None

    def search(self, text, limit):
        words = {w.strip("?.,!").lower() for w in text.split() if len(w) > 3}
        scored = []
        for note in self.rows.values():
            hits = len(words & set(f"{note.title} {note.body}".lower().split()))
            if hits:
                scored.append(ScoredNote(**note.__dict__, score=float(hits)))
        return sorted(scored, key=lambda n: n.score, reverse=True)[:limit]

    def recent(self, limit):
        return self.page(limit, 0)[0]


@dataclass
class FakeLLM:
    model: str = "test-model:1b"
    reply: str = "From your notes: the server is in rack 4 [#1]."
    installed: bool = True
    reachable: bool = True
    calls: list[list[dict]] = field(default_factory=list)

    def chat(self, messages, *, max_tokens=None):
        if not self.reachable:
            raise LLMUnavailableError("Ollama is not reachable at http://ollama:11434.")
        self.calls.append(messages)
        return ChatResult(
            self.reply, self.model, total_ms=850, load_ms=20, prompt_tokens=120, output_tokens=18
        )

    def info(self):
        if not self.reachable:
            raise LLMUnavailableError("Ollama is not reachable at http://ollama:11434.")
        return ModelInfo(name=self.model, installed=self.installed, ollama_version="0.0.0")


@pytest.fixture
def settings() -> Settings:
    return Settings(database_url="postgresql://unused", migrate_on_start=False)


@pytest.fixture
def notes() -> FakeNotes:
    return FakeNotes()


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(settings, notes, llm) -> TestClient:
    with TestClient(create_app(settings, notes=notes, llm=llm)) as test_client:
        yield test_client
