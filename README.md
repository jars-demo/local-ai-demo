<h1 align="center">Local AI Demo</h1>

<p align="center"><b>Local AI. Zero External APIs. Fully Offline Deployment.</b></p>

<p align="center">
  A hands-on workshop: build a full-stack AI notes assistant with Next.js, FastAPI, PostgreSQL and a<br>
  small language model on Ollama, then ship it to a Linux server with no internet connection.
</p>

<p align="center">
  <a href="https://github.com/jars-demo/local-ai-demo/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/jars-demo/local-ai-demo/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Ollama 0.40.3" src="https://img.shields.io/badge/Ollama-0.40.3-111111">
  <img alt="qwen3:0.6b" src="https://img.shields.io/badge/model-qwen3%3A0.6b-6b46c1">
  <img alt="Python 3.13" src="https://img.shields.io/badge/Python-3.13-3776ab">
  <img alt="Next.js 16" src="https://img.shields.io/badge/Next.js-16-000000">
  <img alt="PostgreSQL 18" src="https://img.shields.io/badge/PostgreSQL-18-336791">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/License-MIT-lightgrey"></a>
</p>

<p align="center">
  <b>Site:</b> <a href="https://local-ai.jishanahmed.in">local-ai.jishanahmed.in</a> ·
  <b>Repository:</b> <a href="https://github.com/jars-demo/local-ai-demo">github.com/jars-demo/local-ai-demo</a>
</p>

> [!IMPORTANT]
> An educational project. A 0.6B-parameter model answers simple questions about short notes and
> can be wrong. The stack has no login and no TLS. It is a working, honest reference, not a product.

You write notes. You ask questions about them. A model running in a container on your own machine
answers, citing the notes it used. No API keys, no cloud inference, and, once installed from the
offline bundle, no internet at all.

- **A real application**: note CRUD, PostgreSQL full-text retrieval, then local inference for
  answers and summaries
- **Small and measurable**: four containers; the whole stack uses about 1.2 GB of memory with the
  model loaded; the model is 523 MB; no GPU
- **A genuine offline pipeline**: one reproducible, checksummed bundle built on a connected machine,
  installed on a disconnected server with `docker load` and `--pull never`
- **Proven, with evidence**: an acceptance test that checks the host and the containers have no
  internet, then writes a note and gets a real answer, and saves a report
- **Eleven workshop modules**, beginner core plus an advanced deployment part; every command says
  what it does, why, and what you should see

## Contents

- [Quick start](#quick-start)
- [Architecture](#architecture)
- [Three promises](#three-promises)
- [The workshop](#the-workshop)
- [Offline bundle workflow](#offline-bundle-workflow)
- [Deploying to an offline server](#deploying-to-an-offline-server)
- [Requirements (measured)](#requirements-measured)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Model and attribution](#model-and-attribution)
- [Testing and CI](#testing-and-ci)
- [Repository layout](#repository-layout)
- [Versions](#versions)
- [Contributing](#contributing)
- [License](#license)

## Quick start

You need [Git](https://git-scm.com/downloads), [Docker](https://docs.docker.com/get-docker/) with the
Compose v2 plugin, a bash shell (Linux, macOS, or Git Bash / WSL on Windows), about 4 GB of free
memory, and internet access for this first setup.

```bash
git clone https://github.com/jars-demo/local-ai-demo.git
cd local-ai-demo
cp .env.example .env            # then set POSTGRES_PASSWORD
./scripts/pull-model.sh         # downloads qwen3:0.6b (523 MB) into a Docker volume
docker compose up -d --build --wait
```

**What it does:** downloads and verifies the model, builds three images, pulls PostgreSQL, and
starts four containers, waiting until every health check passes. **Expected:** four lines ending in
`Healthy`. The first build takes a few minutes.

| URL | What |
|---|---|
| <http://localhost:3000> | The site: overview, live readiness of your stack, workshop, offline guide |
| <http://localhost:3000/app/> | The AI Notes Assistant |
| <http://localhost:3000/api/docs> | The API (Swagger UI), through the same proxy |

Prove it works end to end:

```bash
./scripts/smoke-test.sh
```

**What it does:** checks health, stores a note, asks the model about it, destroys and recreates
every container, then checks the note survived and asks again. **Expected:** `ok` lines, two real
answers such as `'The spare key is in drawer 7. [#3]'`, and `smoke test passed`.

## Architecture

```text
browser ──HTTP :3000──► web (nginx: static site + /api proxy)
                              │  /api → http://backend:8000   (Docker DNS)
               ┌──────────────┴──────── private network, internal: true, no route out ──────────┐
               │  backend (FastAPI) ──SQL──► postgres   [volume local-ai-demo-postgres-data]     │
               │          └─────────HTTP──► ollama     [volume local-ai-demo-ollama-models, ro] │
               └──────────────────────────────────────────────────────────────────────────────────┘
```

| Service | Image | Size | Role | Reachable from |
|---|---|---|---|---|
| `web` | `local-ai-demo-web` | 62.7 MB | nginx (unprivileged): the static Next.js export, `/api` reverse proxy, security headers, rate limit on AI endpoints | your browser, `127.0.0.1:3000` |
| `backend` | `local-ai-demo-backend` | 158 MB | FastAPI: notes, retrieval, prompts, readiness | `web` only |
| `postgres` | `postgres:18.6-alpine3.24` | 304 MB | Notes and a generated full-text index | `backend` only |
| `ollama` | `local-ai-demo-ollama` | 142 MB | Ollama 0.40.3, CPU-only, serving `qwen3:0.6b` | `backend` only |

**How a question is answered** (`POST /api/ask`): PostgreSQL full-text search finds the notes that
share words with the question (falling back to the most recent notes); the backend puts them in the
prompt, labelled `[#id]`, with instructions to answer only from them and cite ids; one call to
Ollama's `/api/chat` produces the answer; the response includes the sources and Ollama's own
timings. No embeddings and no vector database: for a personal notebook, the database you already
run is enough.

`compose.yaml` is the runtime contract and only names images; `compose.override.yaml` (loaded
automatically in development) adds the build steps. The offline bundle ships `compose.yaml` alone,
so the server can neither build nor pull.

## Three promises

| Promise | Meaning | Enforced by | Verified by |
|---|---|---|---|
| **No external AI APIs** | Every answer comes from the model in your container | One model client (`backend/app/llm/ollama.py`) for `http://ollama:11434`, with no pull method and no fallback; `OLLAMA_NO_CLOUD=1` | `backend/tests/test_llm.py` |
| **No internet at runtime** | After installation nothing is downloaded | `docker load`, model restore from a file, `--pull never --no-build`, system fonts only | `./scripts/airgap-test.sh --require-offline-host` on a disconnected server |
| **Strict network isolation** | Even on a connected host, backend, database and model cannot reach the internet | Docker network with `internal: true`; model volume read-only | `./scripts/airgap-test.sh` (checks DNS and TCP from inside, and `ollama pull`) |

## The workshop

About 4 hours. Read on the site at <http://localhost:3000/workshop/> or on GitHub.

| # | Module | Part |
|---|---|---|
| 01 | [Architecture and Prerequisites](workshop/01-architecture.md) | Core |
| 02 | [Images, Containers, Ports and Volumes](workshop/02-containers.md) | Core |
| 03 | [Frontend to Backend over HTTP](workshop/03-frontend-to-backend.md) | Core |
| 04 | [Backend to PostgreSQL](workshop/04-backend-to-postgres.md) | Core |
| 05 | [Docker DNS and Service Networking](workshop/05-docker-networking.md) | Core |
| 06 | [Running and Querying the Local LLM](workshop/06-local-llm.md) | Core |
| 07 | [The Inference API and Model Storage](workshop/07-inference-api.md) | Core |
| 08 | [Multi-stage Builds and Image Optimization](workshop/08-image-optimization.md) | Core |
| 09 | [Packaging a Portable Offline Bundle](workshop/09-offline-bundle.md) | Advanced |
| 10 | [Deploying on Bare-metal Linux without Internet](workshop/10-airgapped-deployment.md) | Advanced |
| 11 | [Acceptance Testing, Troubleshooting and Offline Updates](workshop/11-operations.md) | Advanced |

Each module has a goal, an explanation, commands with **What it does / Why / Expected**,
verification, exercises and a troubleshooting table.

## Offline bundle workflow

On the **connected build machine**:

```bash
./scripts/build-bundle.sh
```

1. Checks the machine (`check-prereqs.sh --build`) and validates `compose.yaml`
2. Runs the backend's unit and PostgreSQL integration tests
3. Builds `web`, `backend` and `ollama`; pulls `postgres`
4. Makes sure the model is downloaded and re-hashes every blob
5. Exports images (`docker save`, re-packed with sorted names and fixed timestamps, `gzip -n`) and
   the model's files; restores the model into a scratch volume and loads it read-only, as the
   server will
6. Writes `manifest.json` (versions, image IDs, architectures, sizes, SHA-256, model license and
   source) and `SHA256SUMS`
7. Packs one archive (sorted, fixed mtime, owner 0) plus its `.sha256`

Result, measured: `dist/local-ai-demo-bundle-1.0.0-linux-amd64.tar`, **774.0 MB**. Two consecutive
builds produced the identical SHA-256. No embedding assets are needed (`"embedding_assets": []`).

## Deploying to an offline server

```bash
sha256sum -c local-ai-demo-bundle-1.0.0-linux-amd64.tar.sha256
sudo tar -xf local-ai-demo-bundle-1.0.0-linux-amd64.tar -C /opt
cd /opt/local-ai-demo-bundle-1.0.0-linux-amd64
./scripts/offline-install.sh                       # --bind 0.0.0.0 to serve your network
./scripts/airgap-test.sh --require-offline-host    # with the server disconnected
```

The installer checks prerequisites, verifies every checksum, loads each image and compares its ID
with the manifest, restores and re-hashes the model and proves Ollama can load it read-only with no
network, writes `.env` with a random database password, starts Compose with
`--pull never --no-build`, and runs the smoke test. The full operator guide is
[docs/offline-deployment.md](docs/offline-deployment.md); it also ships inside the bundle.

**What has been verified, and where.** The whole path (archive checksum, extraction, install, the
acceptance test with `--require-offline-host`, real inference, persistence across a full restart)
passes on a **simulated** offline server: a fresh Docker-in-Docker host on an internal network with no
default route and no DNS, started by `./scripts/airgap-simulate.sh` (also defined as a CI job). It has **not yet
been run by this project on separate physical hardware**. Do that on your server with the acceptance
test and keep the report it writes.

## Requirements (measured)

Measured on a laptop running Docker Desktop (WSL 2, linux/amd64) with 4 CPUs and 7.8 GiB for Docker.
Details and commands: [docs/measurements.md](docs/measurements.md).

| | |
|---|---|
| OS | Linux x86_64 for the offline server (arm64 bundles build but are untested). Docker Desktop on Windows or macOS for the core workshop |
| Docker | Engine 24+, Compose plugin 2.24+ (tested 28.2.2 and 28.5.2) |
| CPU | 2 cores minimum, 4+ recommended; AVX2 helps. About 72 to 80 tokens/s generation measured |
| Memory | 4 GB minimum, 8 GB recommended. Measured: about 1.2 GiB for the stack with the model loaded (Ollama 1.11 GiB), about 180 MiB idle |
| Disk | About 1.2 GB for loaded images and the model, plus the 774 MB bundle during install; 4 GB free recommended |
| GPU | Not needed. NVIDIA optional via `compose.gpu.yaml` and `build-bundle.sh --with-gpu` (not tested by this project) |
| Latency | First answer after a start 2 to 11 s (model load); later answers 0.2 to 2.6 s |

## Troubleshooting

Run `./scripts/diagnose.sh` first: it is read-only and prints a `fix:` line for every problem it finds.

| Symptom | Fix |
|---|---|
| `Set POSTGRES_PASSWORD in .env` | `cp .env.example .env` and set it |
| `port is already allocated` | Set `WEB_PORT` in `.env` |
| `/api/ready` says `"model":"missing: qwen3:0.6b"` | `./scripts/pull-model.sh` (connected) or `./scripts/offline-install.sh` (offline) |
| `ollama is unhealthy` on an offline server | Re-run `./scripts/offline-install.sh`; it restores the model and tests it read-only |
| PostgreSQL `password authentication failed` | The data volume keeps its original password; put it back in `.env` |
| First answer is slow | The model loads into memory once (seconds), then stays loaded for 30 minutes |
| `429 Too Many Requests` | nginx rate-limits AI endpoints to protect the CPU; wait a few seconds |
| `LLM_TIMEOUT` | Slow CPU: raise `LLM_TIMEOUT_SECONDS` in `.env` |

Each workshop module ends with its own troubleshooting table.

## Security

- **Network:** one published port, bound to `127.0.0.1` by default (`WEB_BIND`). Backend, database
  and model are on an internal network and cannot reach the internet. The page's
  Content-Security-Policy allows `connect-src 'self'` only.
- **Containers:** non-root users, read-only root filesystems, `cap_drop: [ALL]`,
  `no-new-privileges`, memory limits; the model store is mounted read-only.
- **Secrets:** the only secret is `POSTGRES_PASSWORD`, in `.env` (ignored by Git; mode 600 and
  randomly generated by the offline installer). No API keys exist. `.dockerignore` files keep `.env`,
  bundles and models out of every build context. Logs never contain notes, questions or answers.
- **Input:** strict request schemas (unknown fields rejected, length limits), parameterised SQL,
  database check constraints, `client_max_body_size 64k`, and a rate limit on AI endpoints.
- **Not included:** authentication and TLS. For anything beyond single-user use on one machine, put
  the stack behind a reverse proxy that provides both, and restrict port 3000 with a firewall.
- **Supply chain:** every base image, package and GitHub Action is pinned; the bundle's
  `manifest.json` and `SHA256SUMS` let you verify every artifact offline.

## Model and attribution

- **Qwen3 0.6B** (`qwen3:0.6b`, Q4_K_M, 523 MB) by the Qwen team, Alibaba Cloud, under the
  **Apache License 2.0**. Distributed by Ollama at <https://ollama.com/library/qwen3>; downloaded and
  verified by SHA-256, not modified. Chosen over `qwen2.5:0.5b` after a small workshop-specific
  comparison ([docs/measurements.md](docs/measurements.md)).
- **Ollama 0.40.3**, MIT. `local-ai-demo-ollama` repackages the official image's CPU files unchanged.
- PostgreSQL, nginx, Python, Node.js, FastAPI and the other dependencies under their own licenses:
  [docs/third-party-notices.md](docs/third-party-notices.md).

## Testing and CI

```bash
cd backend && uv run pytest                                   # 35 unit tests, no Docker
docker compose --profile test run --rm --build backend-test   # 47 tests incl. PostgreSQL integration
cd frontend && npm run lint && npm run typecheck && npm run build && npm run build:static
./scripts/smoke-test.sh                                       # against the running stack
./scripts/build-bundle.sh && ./scripts/airgap-simulate.sh     # the offline path, end to end
```

[GitHub Actions](.github/workflows/ci.yml) runs, without secrets or AI credentials: backend lint and
tests (with a PostgreSQL service), frontend lint, typecheck, format and both builds, shellcheck,
Compose validation, Docker image builds with size report, and an end-to-end job that builds the
bundle (downloading the model), verifies its checksums, and installs it on a simulated offline server.

## Repository layout

```text
compose.yaml              the runtime stack (ships in the bundle)
compose.override.yaml     development: build steps and the backend-test service
compose.gpu.yaml          optional NVIDIA GPU override
backend/                  FastAPI app (app/), migrations, tests (unit + integration), Dockerfile
frontend/                 Next.js static site and assistant UI, nginx.conf, Dockerfile
ollama/Dockerfile         CPU-only Ollama image built from the official one
scripts/                  check-prereqs, pull-model, build-bundle, verify-bundle, offline-install,
                          smoke-test, airgap-test, airgap-simulate, diagnose
tests/airgap/             the simulated offline server image
workshop/01..11-*.md      the workshop (the site renders these files)
docs/                     offline deployment guide, measurements, notices, contributing, changelog
```

## Versions

| Component | Version |
|---|---|
| Model | `qwen3:0.6b` |
| Ollama | 0.40.3 (`ollama/ollama:0.40.3`, slim build on `ubuntu:noble-20260917`) |
| PostgreSQL | `postgres:18.6-alpine3.24` |
| Python | 3.13 (`python:3.13.16-slim-trixie`), FastAPI 0.143.0, psycopg 3.3.6, uv 0.13.0 |
| Node.js | 22 (`node:22.23.3-alpine`), Next.js 16.4.0, React 19.3.0, Tailwind CSS 4.3.3 |
| nginx | `nginxinc/nginx-unprivileged:1.31.6-alpine` |

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) and [AGENTS.md](AGENTS.md). Part of
[JARS Demo](https://github.com/jars-demo); this repository follows the
[JARS Skills](https://github.com/jars-demo/jars-skills) playbooks
([skills.jishanahmed.in](https://skills.jishanahmed.in)).

## License

[MIT](LICENSE) for this project's code and docs. The model and third-party software keep their own
licenses: [docs/third-party-notices.md](docs/third-party-notices.md).
