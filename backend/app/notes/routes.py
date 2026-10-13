"""CRUD routes for notes. Handlers are plain `def`: FastAPI runs them in a thread pool, which
suits the blocking psycopg client and keeps the code easy to read."""

from dataclasses import asdict

from fastapi import APIRouter, Query, Request, Response, status

from app.core.errors import NoteNotFoundError
from app.dependencies import get_notes
from app.notes.schemas import NoteCreate, NoteList, NoteOut, NoteUpdate, PageMeta

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", summary="List notes, newest first")
def list_notes(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> NoteList:
    rows, total = get_notes(request).page(limit, offset)
    return NoteList(
        data=[NoteOut(**asdict(row)) for row in rows],
        meta=PageMeta(total=total, limit=limit, offset=offset),
    )


@router.post("", summary="Create a note", status_code=status.HTTP_201_CREATED)
def create_note(request: Request, payload: NoteCreate, response: Response) -> NoteOut:
    note = get_notes(request).create(payload.title, payload.body)
    response.headers["Location"] = f"/api/notes/{note.id}"
    return NoteOut(**asdict(note))


@router.get("/{note_id}", summary="Get one note")
def get_note(request: Request, note_id: int) -> NoteOut:
    note = get_notes(request).get(note_id)
    if note is None:
        raise NoteNotFoundError(note_id)
    return NoteOut(**asdict(note))


@router.patch("/{note_id}", summary="Change a note's title or body")
def update_note(request: Request, note_id: int, payload: NoteUpdate) -> NoteOut:
    note = get_notes(request).update(note_id, payload.title, payload.body)
    if note is None:
        raise NoteNotFoundError(note_id)
    return NoteOut(**asdict(note))


@router.delete("/{note_id}", summary="Delete a note", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(request: Request, note_id: int) -> Response:
    if not get_notes(request).delete(note_id):
        raise NoteNotFoundError(note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
