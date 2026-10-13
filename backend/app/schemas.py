"""Request and response shapes. Unknown request fields are rejected, not silently ignored."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Body = Annotated[str, StringConstraints(max_length=20000)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class AskRequest(Strict):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class SourceOut(BaseModel):
    id: int
    title: str
    score: float | None = Field(
        description="Full-text rank; null when retrieval fell back to recent notes"
    )


class Inference(BaseModel):
    """What the local model did. Every number comes from Ollama's response."""

    model: str
    total_ms: int
    load_ms: int
    prompt_tokens: int
    output_tokens: int


class AskResponse(BaseModel):
    answer: str
    retrieval: Literal["search", "recent", "none"]
    sources: list[SourceOut]
    retrieval_ms: int
    inference: Inference | None


class SummaryResponse(BaseModel):
    note_id: int
    summary: str
    inference: Inference


class ModelOut(BaseModel):
    name: str
    installed: bool
    ollama_version: str | None
    size_bytes: int | None
    digest: str | None
    family: str | None
    parameter_size: str | None
    quantization: str | None
    context_length: int | None


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, str]
