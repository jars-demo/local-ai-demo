"""Accessors for the objects `create_app()` puts on `app.state`. Routes use these, never globals,
so tests can run the real routes against fakes."""

from fastapi import Request

from app.core.config import Settings
from app.llm.ollama import LLM
from app.notes.models import Notes


def get_notes(request: Request) -> Notes:
    return request.app.state.notes


def get_llm(request: Request) -> LLM:
    return request.app.state.llm


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
