"""Liveness, readiness and model information."""

from dataclasses import asdict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.dependencies import get_llm, get_notes
from app.health.schemas import ModelOut, ReadyResponse

router = APIRouter()


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
        get_notes(request).ping()
        checks["database"] = "ok"
    except Exception as exc:  # readiness reports every failure instead of raising
        checks["database"] = f"error: {type(exc).__name__}"
    try:
        info = get_llm(request).info()
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
    return ModelOut(**asdict(get_llm(request).info()))
