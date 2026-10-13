"""Application errors and the one JSON error shape every endpoint returns.

    {"error": {"code": "NOTE_NOT_FOUND", "message": "...", "hint": "...", "fields": {...}}}

`hint` is optional and tells the operator what to do next (for example, how to install the model).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.hint = hint


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class NoteNotFoundError(NotFoundError):
    code = "NOTE_NOT_FOUND"

    def __init__(self, note_id: int):
        super().__init__(f"Note {note_id} does not exist.")


class LLMUnavailableError(AppError):
    """Ollama cannot be reached. The backend never falls back to another provider."""

    status_code = 503
    code = "LLM_UNAVAILABLE"


class ModelNotInstalledError(AppError):
    status_code = 503
    code = "MODEL_NOT_INSTALLED"


class LLMTimeoutError(AppError):
    status_code = 504
    code = "LLM_TIMEOUT"


class LLMError(AppError):
    status_code = 502
    code = "LLM_ERROR"


class DatabaseUnavailableError(AppError):
    status_code = 503
    code = "DATABASE_UNAVAILABLE"


def _body(code: str, message: str, hint: str | None = None, fields: dict | None = None) -> dict:
    error: dict = {"code": code, "message": message}
    if hint:
        error["hint"] = hint
    if fields:
        error["fields"] = fields
    return {"error": error}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        level = logging.WARNING if exc.status_code < 500 else logging.ERROR
        log.log(level, "request failed", extra={"path": request.url.path, "code": exc.code})
        return JSONResponse(
            status_code=exc.status_code, content=_body(exc.code, exc.message, exc.hint)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = {}
        for err in exc.errors():
            location = ".".join(str(part) for part in err["loc"] if part != "body")
            fields[location or "body"] = err["msg"]
        return JSONResponse(
            status_code=422,
            content=_body("VALIDATION_FAILED", "The request is not valid.", None, fields),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)))

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled error", extra={"path": request.url.path}, exc_info=exc)
        return JSONResponse(
            status_code=500, content=_body("INTERNAL_ERROR", "An unexpected error occurred.")
        )
