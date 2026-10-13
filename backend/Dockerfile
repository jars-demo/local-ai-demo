# The backend API. Build from backend/:
#
#   docker build -t local-ai-demo-backend backend/
#
# Stages: `build` resolves dependencies with uv into a virtualenv; `test` adds the dev tools and
# the tests (used by `docker compose --profile test run backend-test`); `runtime` copies only the
# virtualenv and the source onto a slim Python image, so uv, caches and tests never ship.

ARG PYTHON_IMAGE=python:3.13.16-slim-trixie
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.0

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
# Dependencies first, in their own layer: editing the source does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM build AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
COPY app/ ./app/
COPY tests/ ./tests/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["pytest", "-m", "integration or not integration", "-q"]

FROM ${PYTHON_IMAGE} AS runtime
LABEL org.opencontainers.image.title="local-ai-demo-backend" \
      org.opencontainers.image.description="Local AI Notes Assistant API (FastAPI)" \
      org.opencontainers.image.source="https://github.com/jars-demo/local-ai-demo" \
      org.opencontainers.image.licenses="MIT"
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY app/ ./app/
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER 10001
EXPOSE 8000
# Liveness only. Readiness (database, Ollama, model) is /api/ready, checked by the smoke test.
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=6 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]
CMD ["python", "-m", "app"]
