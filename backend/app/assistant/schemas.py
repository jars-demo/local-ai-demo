"""Request and response shapes for the AI endpoints."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.core.schemas import Strict
from app.llm.ollama import ChatResult


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

    @classmethod
    def from_chat(cls, chat: ChatResult) -> "Inference":
        return cls(
            model=chat.model,
            total_ms=chat.total_ms,
            load_ms=chat.load_ms,
            prompt_tokens=chat.prompt_tokens,
            output_tokens=chat.output_tokens,
        )


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
