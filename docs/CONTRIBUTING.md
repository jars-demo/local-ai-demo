# Contributing

Thanks for helping. This is a teaching project: clear beats clever, and every claim must be true.

## Ground rules

1. **No external AI services.** No code path may call a hosted model, an API key, or download a
   model at runtime. The only model client is `backend/app/llm/ollama.py`, for Ollama on the private
   network. `tests/test_llm.py` enforces that it cannot pull.
2. **Verify before documenting.** Run every command you add to `workshop/` or `docs/` against the
   stack, and paste real output. No invented numbers: measurements go through `docs/measurements.md`.
3. **The offline path stays offline.** `compose.yaml` never gets a `build:` section (that lives in
   `compose.override.yaml`). Offline scripts never pull. The private network stays `internal: true`.
4. **Pins move together.** Image tags in `compose.yaml` and Dockerfiles, `backend/uv.lock`,
   `frontend/package-lock.json`, the README version table and `frontend/src/lib/site.ts`. Actions
   are pinned to commit SHAs.

## Set up

```bash
cp .env.example .env
./scripts/pull-model.sh
docker compose up -d --build --wait
```

Backend (Python 3.13, [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync
uv run pytest                                   # unit tests, no Docker needed
uv run ruff check . && uv run ruff format --check .
cd .. && docker compose --profile test run --rm --build backend-test   # + integration tests
```

Frontend (Node.js 22):

```bash
cd frontend
npm ci
npm run lint && npm run typecheck && npm run format:check && npm run build && npm run build:static
NEXT_PUBLIC_API_URL=http://localhost:3000 npm run dev    # http://localhost:3001 against the stack
```

Scripts: `shellcheck -x -P SCRIPTDIR scripts/*.sh`. End to end: `./scripts/build-bundle.sh` then
`./scripts/airgap-simulate.sh`.

## Changes

- One concern per pull request. Tests for new behaviour (`backend/tests/`), and the docs that the
  change affects (`workshop/`, `docs/`, README).
- A new workshop module needs its file in `workshop/` and an entry in `frontend/src/lib/chapters.ts`.
- Commits: Conventional Commits, `type(scope): Imperative summary`, with a body that says why.
- Writing style: plain English, no em dashes. Every command in a module has **What it does**,
  **Why** and **Expected**.

## Reporting a problem

Run `./scripts/diagnose.sh`, review the output (it never prints the database password, but check it
for anything else you consider private), and attach it to the issue with your OS, Docker version and
what you ran.
