"""Prompts: what the model is told, and how notes are put in front of it. Pure functions."""

from app.notes.models import Note

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
