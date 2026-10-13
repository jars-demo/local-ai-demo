# 01 · Architecture and Prerequisites

> ⏱ 20 minutes · The four services, what "offline" really means, and getting your machine ready.

## Goal

Know what you are about to run, why each piece exists, and confirm your machine can run it.

## What you'll learn

- The four containers and the one job each does
- Three different promises: no external AI APIs, no internet at runtime, strict network isolation
- What your machine needs, measured on a real run

## Architecture

```text
browser ──HTTP :3000──► web (nginx) ──/api──► backend (FastAPI) ──SQL──► postgres
                                                        └──HTTP──► ollama ──► qwen3:0.6b
          edge network ◄──────────────┘└──────────── private network (internal: true) ────────────┘
```

| Service | Image | Job |
|---|---|---|
| `web` | `local-ai-demo-web` (nginx) | Serves this site and the assistant UI; forwards `/api/*` to the backend |
| `backend` | `local-ai-demo-backend` (FastAPI) | Notes API, retrieval, prompts; the only service that talks to the model |
| `postgres` | `postgres:18.6-alpine3.24` | Stores notes and a full-text index of them |
| `ollama` | `local-ai-demo-ollama` (Ollama 0.40.3, CPU) | Runs the model `qwen3:0.6b` (523 MB, Apache 2.0) |

The model is not inside any image. It lives in a Docker volume, `local-ai-demo-ollama-models`, and
reaches it either by download (on a connected machine) or from the offline bundle.

## Three promises, kept apart

People often say "offline AI" and mean one of three different things. This workshop keeps them
separate because each is enforced, and tested, in a different place.

| Promise | What it means | Where it is enforced |
|---|---|---|
| **No external AI APIs** | Answers come from a model in your container. No API keys, no cloud inference. | The backend has one model client, for `http://ollama:11434`, with no download method and no fallback. Ollama runs with `OLLAMA_NO_CLOUD=1`. |
| **No internet at runtime** | Once installed, nothing is downloaded: no images, no model, no fonts. | The offline installer uses `docker load` and `--pull never`. The site uses system fonts. |
| **Strict network isolation** | Even if the host is online, backend, database and model cannot reach the internet. | They sit on a Docker network with `internal: true`. The model volume is read-only. |

The first is true on any machine running this stack. The second is true once you install from the
bundle (module 10). The third is true everywhere the stack runs, and module 11 proves it.

## Prerequisites

- **Git** and **Docker** with the **Compose v2 plugin** (`docker compose`, not `docker-compose`).
  Docker Engine 24+ on Linux, or Docker Desktop on Windows or macOS.
- A **bash** shell. Linux and macOS have one. On Windows, use **Git Bash** or **WSL**.
- About **4 GB free memory** and **4 GB free disk**. No GPU.
- Internet access for this first part (to download images and the model). Module 10 removes it.

Measured on a laptop running Docker Desktop with 4 CPUs and 7.8 GiB for Docker: the whole stack used
about 1.2 GB of memory with the model loaded (Ollama 1.11 GiB of it).

## Steps

### 1. Get the code

```bash
git clone https://github.com/jars-demo/local-ai-demo.git
cd local-ai-demo
```

> **What it does:** Downloads the repository and enters it.
> **Why:** Every command in this workshop runs from the repository root.
> **Expected:** A folder with `compose.yaml`, `backend/`, `frontend/`, `ollama/`, `scripts/`, `workshop/`.

### 2. Check your machine

```bash
./scripts/check-prereqs.sh --build
```

> **What it does:** Checks the OS and architecture, Docker and Compose versions, CPU cores, AVX2,
> memory, free disk, the tools the scripts use, and that the model registry is reachable.
> **Why:** A failed check here costs a minute; the same problem found halfway through module 06
> costs much more.
> **Expected:** A list of `ok` lines ending with `this machine meets the requirements (build)`. On
> Windows or macOS you also see one `warn`: the offline target itself must be Linux.

### 3. Create your configuration

```bash
cp .env.example .env
```

Open `.env` and set `POSTGRES_PASSWORD` to any value you like. Leave the rest as it is.

> **What it does:** Creates the file Compose reads variables from.
> **Why:** The database password must not live in Git. `.env` is in `.gitignore`; `.env.example`
> is the template that is committed.
> **Expected:** A `.env` file. `git status` does not list it.

## Verification

- [ ] `./scripts/check-prereqs.sh --build` ends with `meets the requirements`
- [ ] `.env` exists and `git status` does not show it
- [ ] You can name the four services and say which one talks to the model

## Exercises

1. Read `compose.yaml` top to bottom. Find the one `ports:` entry. Which service has it, and which
   address is it bound to?
2. In `compose.yaml`, find `internal: true`. Which services are on that network?
3. Without running anything, predict: can the browser call `postgres` directly? Why not?

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `docker: command not found` | Docker is not installed | Install Docker Engine (Linux) or Docker Desktop |
| `the Docker daemon is not reachable` | Docker is not running, or your user lacks access | Start Docker; on Linux add yourself to the `docker` group and log in again |
| `the Docker Compose v2 plugin is missing` | Only the old `docker-compose` is installed | Install the `docker-compose-plugin` package |
| `Permission denied` running a script | Execute bit lost (for example, copied through Windows) | `chmod +x scripts/*.sh` |
| Memory check fails on Docker Desktop | Docker's VM has too little memory | Docker Desktop: Settings, Resources, Memory: 6 GB or more |

Next: [02 · Images, Containers, Ports and Volumes](02-containers.md)
