"""Response shapes for readiness and model information."""

from typing import Literal

from pydantic import BaseModel


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, str]


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
