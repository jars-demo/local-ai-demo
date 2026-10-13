# AGENTS.md

Guidance for AI coding agents and developers working in this repository. Humans: start with
[README.md](README.md).

## What this is

A workshop and a working reference: an AI Notes Assistant (Next.js static site served by nginx,
FastAPI, PostgreSQL 18, Ollama 0.40.3 with `qwen3:0.6b` on the CPU) and a connected-build to
air-gapped-deployment pipeline. Eleven workshop modules. Learners read the code, so prefer clear
over clever. It is educational: never present it as production-ready.

## Map

```text
compose.yaml                   runtime contract, images only, ships in the bundle
compose.override.yaml          dev only: build steps, backend-test (integration tests, notes_test DB)
backend/app/main.py            app factory, request logging; __main__.py runs Uvicorn; api.py mounts /api
backend/app/core/              config.py (env, service names not localhost), errors.py, logs.py, schemas.py
backend/app/db/                migrate.py + migrations/ (numbered up/down SQL, advisory lock)
backend/app/notes/             models.py (Note, Notes protocol), repository.py (parameterised SQL,
                               full-text search), schemas.py, routes.py (CRUD)
backend/app/llm/ollama.py      OllamaClient: chat, info. NO pull method, no fallback provider
backend/app/assistant/         prompts.py, service.py (retrieval then inference), schemas.py, routes.py
backend/app/health/            /api/health, /api/ready, /api/model
backend/tests/                 unit tests with fakes; tests/integration needs real PostgreSQL
frontend/src/lib/              site.ts (versions, nav), chapters.ts (keep in step with workshop/),
                               api.ts (client), measurements.ts (only measured numbers)
frontend/nginx.conf            /api proxy via Docker DNS, CSP, rate limit
ollama/Dockerfile              CPU-only repackaging of the official image
scripts/                       bash; lib.sh shared; offline scripts must never pull
tests/airgap/                  Docker-in-Docker image for scripts/airgap-simulate.sh
workshop/NN-*.md               modules 01 to 11 (source of truth, rendered by the site)
docs/                          offline-deployment.md (ships as the bundle README), measurements.md
```

## Commands

```bash
cp .env.example .env && ./scripts/pull-model.sh && docker compose up -d --build --wait
./scripts/smoke-test.sh
cd backend && uv sync && uv run pytest && uv run ruff check . && uv run ruff format --check .
docker compose --profile test run --rm --build backend-test
cd frontend && npm ci && npm run lint && npm run typecheck && npm run format:check && npm run build && npm run build:static
shellcheck -x -P SCRIPTDIR scripts/*.sh
./scripts/build-bundle.sh && ./scripts/airgap-simulate.sh
```

## Rules

1. **No external AI.** Never add a hosted model, an API key, a model download at runtime, or a
   fallback provider. `OllamaClient` must not gain a pull method (a test enforces it).
2. **Offline means offline.** No `build:` in `compose.yaml`. Offline scripts use `docker load`,
   `--pull never`, `--no-build`, and fail loudly instead of reaching a registry. The private network
   stays `internal: true`; the model volume stays read-only at runtime.
3. **Verify before documenting.** Run every command you document and paste real output. Numbers go
   through `docs/measurements.md` and `frontend/src/lib/measurements.ts`. Never claim a physical
   air-gapped test that was not run; say "simulated" when it was.
4. **Docs follow code.** A changed command, path, port, size or output means updated `workshop/`,
   `docs/` and README. A new module needs `frontend/src/lib/chapters.ts`.
5. **Pins move together** (see docs/CONTRIBUTING.md). GitHub Actions are pinned to commit SHAs.
6. **Hardening stays on.** Non-root, read-only root filesystems, `cap_drop: [ALL]`,
   `no-new-privileges`, memory limits, one published port on `127.0.0.1` by default.
7. **Never commit** `.env`, `dist/`, model files, `node_modules/`, `.next/`, `out/`, `.venv/`.
8. **Writing style.** Plain English, no em dashes. Commands in modules have **What it does / Why /
   Expected**. Modules have Goal, What you'll learn, Architecture, Prerequisites, Steps,
   Verification, Exercises, Troubleshooting.
9. **Root files.** Only `README.md`, `AGENTS.md` and `LICENSE` at the root; other documents in
   `docs/` or `workshop/`.
10. **No AI attribution.** No co-author trailers, generated-by credits or tool branding in commits,
    files or the site.

## Brand

Same as the other JARS Demo sites: white-first, primary `#2563EB`, ink `#0F172A`, tokens in
`frontend/src/app/globals.css`, status shown with shape and label as well as colour, no decorative
animation, no AI imagery. System fonts only (no font downloads: the site must work offline).

## Skills

This repository follows the [JARS Skills](https://github.com/jars-demo/jars-skills) playbooks:
`env-setup`, `api-design`, `sql-query`, `migrate-db`, `docker`, `debug-infra-startup`, `logging`,
`error-handling`, `write-tests`, `accessibility`, `ci-cd`, `code-review`, `commit-style`,
`pr-description`, `changelog` and `release`. Never push, tag or publish unless asked.
