"""HTTP routes. Handlers are plain `def`: FastAPI runs them in a thread pool, which suits the
blocking psycopg and httpx clients and keeps the code easy to read."""

from dataclasses import asdict

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import JSONResponse

from app.assistant import answer_question, summarise
from app.config import Settings
from app.errors import AppError, NoteNotFoundError
from app.llm import LLM, ChatResult
from app.notes import Notes
from app.schemas import (
    AskRequest,
    AskResponse,
    Inference,
    ModelOut,
    NoteCreate,
    NoteList,
    NoteOut,
    NoteUpdate,
    PageMeta,
    ReadyResponse,
    SourceOut,
    SummaryResponse,
)

router = APIRouter(prefix="/api")


def _notes(request: Request) -> Notes:
    return request.app.state.notes


def _llm(request: Request) -> LLM:
    return request.app.state.llm


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _inference(chat: ChatResult) -> Inference:
    return Inference(
        model=chat.model,
        total_ms=chat.total_ms,
        load_ms=chat.load_ms,
        prompt_tokens=chat.prompt_tokens,
        output_tokens=chat.output_tokens,
    )


# --- Health ------------------------------------------------------------------------------------


@router.get("/health", tags=["health"], summary="Liveness: the process serves HTTP")
def health() -> dict:
    return {"status": "ok"}


@router.get(
    "/ready",
    tags=["health"],
    summary="Readiness: database, Ollama and the configured model",
    response_model=ReadyResponse,
    responses={503: {"model": ReadyResponse}},
)
def ready(request: Request) -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        _notes(request).ping()
        checks["database"] = "ok"
    except Exception as exc:  # readiness reports every failure instead of raising
        checks["database"] = f"error: {type(exc).__name__}"
    try:
        info = _llm(request).info()
        checks["ollama"] = "ok"
        checks["model"] = "ok" if info.installed else f"missing: {info.name}"
    except AppError as exc:
        checks["ollama"] = f"error: {exc.code}"
        checks["model"] = "unknown"
    ok = all(value == "ok" for value in checks.values())
    body = ReadyResponse(status="ready" if ok else "not_ready", checks=checks)
    return JSONResponse(body.model_dump(), status_code=200 if ok else 503)


@router.get("/model", tags=["model"], summary="The local model: name, size, quantisation")
def model(request: Request) -> ModelOut:
    return ModelOut(**asdict(_llm(request).info()))


# --- Notes -------------------------------------------------------------------------------------


@router.get("/notes", tags=["notes"], summary="List notes, newest first")
def list_notes(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> NoteList:
    rows, total = _notes(request).page(limit, offset)
    return NoteList(
        data=[NoteOut(**asdict(row)) for row in rows],
        meta=PageMeta(total=total, limit=limit, offset=offset),
    )


@router.post("/notes", tags=["notes"], summary="Create a note", status_code=status.HTTP_201_CREATED)
def create_note(request: Request, payload: NoteCreate, response: Response) -> NoteOut:
    note = _notes(request).create(payload.title, payload.body)
    response.headers["Location"] = f"/api/notes/{note.id}"
    return NoteOut(**asdict(note))


@router.get("/notes/{note_id}", tags=["notes"], summary="Get one note")
def get_note(request: Request, note_id: int) -> NoteOut:
    note = _notes(request).get(note_id)
    if note is None:
        raise NoteNotFoundError(note_id)
    return NoteOut(**asdict(note))


@router.patch("/notes/{note_id}", tags=["notes"], summary="Change a note's title or body")
def update_note(request: Request, note_id: int, payload: NoteUpdate) -> NoteOut:
    note = _notes(request).update(note_id, payload.title, payload.body)
    if note is None:
        raise NoteNotFoundError(note_id)
    return NoteOut(**asdict(note))


@router.delete(
    "/notes/{note_id}",
    tags=["notes"],
    summary="Delete a note",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_note(request: Request, note_id: int) -> Response:
    if not _notes(request).delete(note_id):
        raise NoteNotFoundError(note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- AI ----------------------------------------------------------------------------------------


@router.post(
    "/notes/{note_id}/summary",
    tags=["ai"],
    summary="Summarise one note with the local model",
)
def summarise_note(request: Request, note_id: int) -> SummaryResponse:
    note = _notes(request).get(note_id)
    if note is None:
        raise NoteNotFoundError(note_id)
    chat = summarise(note, _llm(request), note_chars=_settings(request).note_chars_in_prompt * 2)
    return SummaryResponse(note_id=note_id, summary=chat.text, inference=_inference(chat))


@router.post(
    "/ask",
    tags=["ai"],
    summary="Ask a question; relevant notes are retrieved first, then the local model answers",
)
def ask(request: Request, payload: AskRequest) -> AskResponse:
    settings = _settings(request)
    result = answer_question(
        payload.question,
        _notes(request),
        _llm(request),
        max_notes=settings.max_context_notes,
        note_chars=settings.note_chars_in_prompt,
    )
    return AskResponse(
        answer=result.text,
        retrieval=result.retrieval,
        sources=[SourceOut(id=s.id, title=s.title, score=s.score) for s in result.sources],
        retrieval_ms=result.retrieval_ms,
        inference=_inference(result.chat) if result.chat else None,
    )
