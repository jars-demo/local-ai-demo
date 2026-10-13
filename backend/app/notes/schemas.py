"""Request and response shapes for /api/notes."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints, model_validator

from app.core.schemas import Strict

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Body = Annotated[str, StringConstraints(max_length=20000)]


class NoteCreate(Strict):
    title: Title
    body: Body = ""


class NoteUpdate(Strict):
    title: Title | None = None
    body: Body | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "NoteUpdate":
        if self.title is None and self.body is None:
            raise ValueError("send at least one of: title, body")
        return self


class NoteOut(BaseModel):
    id: int
    title: str
    body: str
    created_at: datetime
    updated_at: datetime


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int


class NoteList(BaseModel):
    data: list[NoteOut]
    meta: PageMeta
