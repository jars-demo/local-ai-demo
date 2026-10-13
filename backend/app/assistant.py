"""Retrieval, then inference: the whole "AI" part of the app, in plain Python.

1. Retrieve: PostgreSQL full-text search finds the notes that share words with the question.
   If nothing matches, the most recently edited notes are used instead, and the answer says so.
2. Prompt: the retrieved notes go into the prompt, each labelled with its id, with an instruction
   to answer only from them.
3. Infer: one call to the local model through Ollama.

No embeddings, no vector database and no agent loop: for a personal notebook, keyword search in
the database you already run is enough, and every step is visible in the response.
"""

import time
from dataclasses import dataclass, field
from typing import Literal

from app.llm import LLM, ChatResult
from app.notes import Note, Notes

ASK_SYSTEM = (
    "You are a notes assistant. Answer the question using only the notes provided. "
    "Cite the notes you used by their id in square brackets, for example [#3]. "
    "If the notes do not contain the answer, say that the notes do not cover it. "
    "Be concise: at most five sentences."
)

SUMMARY_SYSTEM = (
    "You summarise personal notes. Write a summary of the note in two or three sentences, "
    "then up to three short bullet points with any action items. Use only the note's content."
)

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


def clip(text: str, limit: int) -> str:
    """Shorten text to `limit` characters on a word boundary, marking the cut."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return f"{cut} [...]"


def format_note(note: Note, limit: int) -> str:
    return f"[#{note.id}] {note.title}\n{clip(note.body, limit)}"


def build_ask_messages(question: str, notes: list[Note], note_chars: int) -> list[dict]:
    context = "\n\n".join(format_note(note, note_chars) for note in notes)
    return [
        {"role": "system", "content": ASK_SYSTEM},
        {"role": "user", "content": f"Notes:\n\n{context}\n\nQuestion: {question}"},
    ]


def build_summary_messages(note: Note, note_chars: int) -> list[dict]:
    return [
        {"role": "system", "content": SUMMARY_SYSTEM},
        {"role": "user", "content": format_note(note, note_chars)},
    ]


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
