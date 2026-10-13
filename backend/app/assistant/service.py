"""Retrieval, then inference: the whole "AI" part of the app, in plain Python.

1. Retrieve: PostgreSQL full-text search finds the notes that share words with the question.
   If nothing matches, the most recently edited notes are used instead, and the answer says so.
2. Prompt: the retrieved notes go into the prompt (see prompts.py), each labelled with its id.
3. Infer: one call to the local model through Ollama.

No embeddings, no vector database and no agent loop: for a personal notebook, keyword search in
the database you already run is enough, and every step is visible in the response.
"""

import time
from dataclasses import dataclass, field
from typing import Literal

from app.assistant.prompts import build_ask_messages, build_summary_messages
from app.llm.ollama import LLM, ChatResult
from app.notes.models import Note, Notes

Retrieval = Literal["search", "recent", "none"]


@dataclass
class Source:
    id: int
    title: str
    score: float | None


@dataclass
class Answer:
    text: str
    retrieval: Retrieval
    sources: list[Source] = field(default_factory=list)
    chat: ChatResult | None = None
    retrieval_ms: int = 0


def answer_question(
    question: str, notes: Notes, llm: LLM, *, max_notes: int, note_chars: int
) -> Answer:
    started = time.perf_counter()
    found = notes.search(question, max_notes)
    retrieval: Retrieval = "search"
    context: list[Note] = list(found)
    if not context:
        context = notes.recent(max_notes)
        retrieval = "recent"
    retrieval_ms = round((time.perf_counter() - started) * 1000)

    if not context:
        return Answer(
            text="You have no notes yet. Add a note, then ask about it.",
            retrieval="none",
            retrieval_ms=retrieval_ms,
        )

    chat = llm.chat(build_ask_messages(question, context, note_chars))
    sources = [Source(n.id, n.title, getattr(n, "score", None)) for n in context]
    return Answer(chat.text, retrieval, sources, chat, retrieval_ms)


def summarise(note: Note, llm: LLM, *, note_chars: int) -> ChatResult:
    return llm.chat(build_summary_messages(note, note_chars), max_tokens=256)
