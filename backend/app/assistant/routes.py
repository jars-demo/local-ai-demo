"""The AI endpoints: summarise a note, and ask a question about all notes."""

from fastapi import APIRouter, Request

from app.assistant.schemas import AskRequest, AskResponse, Inference, SourceOut, SummaryResponse
from app.assistant.service import answer_question, summarise
from app.core.errors import NoteNotFoundError
from app.dependencies import get_llm, get_notes, get_settings

router = APIRouter(tags=["ai"])


@router.post("/notes/{note_id}/summary", summary="Summarise one note with the local model")
def summarise_note(request: Request, note_id: int) -> SummaryResponse:
    note = get_notes(request).get(note_id)
    if note is None:
        raise NoteNotFoundError(note_id)
    note_chars = get_settings(request).note_chars_in_prompt * 2
    chat = summarise(note, get_llm(request), note_chars=note_chars)
    return SummaryResponse(note_id=note_id, summary=chat.text, inference=Inference.from_chat(chat))


@router.post(
    "/ask",
    summary="Ask a question; relevant notes are retrieved first, then the local model answers",
)
def ask(request: Request, payload: AskRequest) -> AskResponse:
    settings = get_settings(request)
    result = answer_question(
        payload.question,
        get_notes(request),
        get_llm(request),
        max_notes=settings.max_context_notes,
        note_chars=settings.note_chars_in_prompt,
    )
    return AskResponse(
        answer=result.text,
        retrieval=result.retrieval,
        sources=[SourceOut(id=s.id, title=s.title, score=s.score) for s in result.sources],
        retrieval_ms=result.retrieval_ms,
        inference=Inference.from_chat(result.chat) if result.chat else None,
    )
