"""The FastAPI application: wiring, request logging and startup.

`create_app()` takes optional `notes` and `llm` objects so tests can run the real routes against
in-memory fakes. In Docker it is called without them and connects to PostgreSQL and Ollama.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request
from psycopg_pool import ConnectionPool

from app.api import router
from app.core.config import Settings
from app.core.errors import install_error_handlers
from app.db import migrate
from app.llm.ollama import LLM, OllamaClient
from app.notes.models import Notes
from app.notes.repository import NoteStore

log = logging.getLogger("app")

VERSION = "1.0.0"


def create_app(
    settings: Settings | None = None, *, notes: Notes | None = None, llm: LLM | None = None
) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        pool = None
        if notes is None:
            if settings.migrate_on_start:
                with psycopg.connect(settings.database_url, autocommit=True) as conn:
                    applied = migrate.upgrade(conn)
                log.info("database schema ready", extra={"migrations_applied": applied})
            pool = ConnectionPool(settings.database_url, min_size=1, max_size=10, open=True)
            app.state.notes = NoteStore(pool)
        log.info(
            "backend started",
            extra={
                "version": VERSION,
                "ollama_url": settings.ollama_url,
                "model": settings.ollama_model,
            },
        )
        yield
        if pool is not None:
            pool.close()

    app = FastAPI(
        title="Local AI Notes Assistant API",
        version=VERSION,
        summary="Notes in PostgreSQL, answers from a local model via Ollama. No external AI APIs.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    if notes is not None:
        app.state.notes = notes
    app.state.llm = llm or OllamaClient(
        settings.ollama_url,
        settings.ollama_model,
        think=settings.ollama_think,
        timeout_seconds=settings.llm_timeout_seconds,
        max_tokens=settings.llm_max_tokens,
        context_tokens=settings.llm_context_tokens,
    )

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        if request.url.path not in ("/api/health",):
            log.info(
                "request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
        return response

    install_error_handlers(app)
    app.include_router(router)
    return app
