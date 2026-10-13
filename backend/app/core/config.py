"""Settings, read once from environment variables.

Every value has a safe default for the Docker Compose stack except the database password, which
must come from the environment (the `.env` file). Service names (`postgres`, `ollama`) are Docker
DNS names on the private network, never `localhost`.
"""

import os
from dataclasses import dataclass

from psycopg.conninfo import make_conninfo


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


@dataclass(frozen=True)
class Settings:
    database_url: str
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen3:0.6b"
    # Qwen3 is a "thinking" model. For short note answers we turn thinking off: faster on a CPU
    # and the answer comes back without a reasoning preamble. Empty means "do not send the flag".
    ollama_think: bool | None = False
    llm_timeout_seconds: float = 180.0
    llm_max_tokens: int = 384
    llm_context_tokens: int = 4096
    max_context_notes: int = 4
    note_chars_in_prompt: int = 1500
    migrate_on_start: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.environ.get("DATABASE_URL", "").strip()
        if not database_url:
            password = os.environ.get("POSTGRES_PASSWORD", "")
            if not password:
                raise RuntimeError(
                    "POSTGRES_PASSWORD is not set. Copy .env.example to .env and set it."
                )
            database_url = make_conninfo(
                host=_env("POSTGRES_HOST", "postgres"),
                port=_env("POSTGRES_PORT", "5432"),
                dbname=_env("POSTGRES_DB", "notes"),
                user=_env("POSTGRES_USER", "notes"),
                password=password,
                connect_timeout="5",
                application_name="local-ai-demo-backend",
            )
        think = _env("OLLAMA_THINK", "false").lower()
        return cls(
            database_url=database_url,
            ollama_url=_env("OLLAMA_URL", cls.ollama_url).rstrip("/"),
            ollama_model=_env("OLLAMA_MODEL", cls.ollama_model),
            ollama_think=None if think == "unset" else think == "true",
            llm_timeout_seconds=float(_env("LLM_TIMEOUT_SECONDS", str(cls.llm_timeout_seconds))),
            llm_max_tokens=int(_env("LLM_MAX_TOKENS", str(cls.llm_max_tokens))),
            llm_context_tokens=int(_env("LLM_CONTEXT_TOKENS", str(cls.llm_context_tokens))),
            max_context_notes=int(_env("MAX_CONTEXT_NOTES", str(cls.max_context_notes))),
            migrate_on_start=_env("MIGRATE_ON_START", "true").lower() == "true",
            log_level=_env("LOG_LEVEL", cls.log_level).upper(),
        )
