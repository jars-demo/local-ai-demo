# 02 · Images, Containers, Ports and Volumes

> ⏱ 25 minutes · Start the stack and see what each Docker building block does.

## Goal

Download the model, start the four containers, and be able to explain the difference between an
image, a container, a port and a volume using this stack as the example.

## What you'll learn

- An **image** is a read-only template; a **container** is a running instance of one
- A **port** mapping is the only door from your machine into the stack
- A **volume** is storage that outlives containers: your notes and the model live in two of them
- Health checks and `depends_on` decide start order, not sleeps

## Architecture

```text
images (templates)              containers (running)          volumes (data that stays)
local-ai-demo-web:1.0.0     ──► web       :8080 ◄── 127.0.0.1:3000
local-ai-demo-backend:1.0.0 ──► backend   :8000
postgres:18.6-alpine3.24    ──► postgres  :5432 ──► local-ai-demo-postgres-data
local-ai-demo-ollama:0.40.3 ──► ollama    :11434 ─► local-ai-demo-ollama-models (read-only)
```

## Prerequisites

Module 01.

## Steps

### 1. Download the model into its volume

```bash
./scripts/pull-model.sh
```

> **What it does:** Builds the Ollama image if needed, creates the volume
> `local-ai-demo-ollama-models`, starts a temporary Ollama container on Docker's default network,
> runs `ollama pull qwen3:0.6b` (which checks every file's SHA-256), then removes that container.
> **Why:** The running stack is not allowed to download anything (module 05 shows why it cannot).
> So the model is installed by this separate, explicit step, once.
> **Expected:** Progress bars, `verifying sha256 digest`, `success`, then a list with
> `qwen3:0.6b    7df6b6e09427    522 MB`.

### 2. Build and start the stack

```bash
docker compose up -d --build --wait
```

> **What it does:** Builds the three application images, pulls `postgres`, creates two networks and
> the data volume, and starts the containers in dependency order. `--wait` returns only when every
> health check passes.
> **Why:** One command, the same on every machine. Compose also reads `compose.override.yaml`,
> which adds the build steps; the offline server does not have that file.
> **Expected:** The first build takes a few minutes. It ends with four lines like
> `Container local-ai-demo-web-1  Healthy`.

### 3. Look at the images

```bash
docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}' | grep -E 'local-ai-demo|postgres'
```

> **What it does:** Lists the images the stack uses and their unpacked sizes.
> **Why:** Images are the unit you build, ship and load. Module 08 explains why these are small.
> **Expected (measured):**
>
> ```text
> postgres:18.6-alpine3.24                    304MB
> local-ai-demo-ollama:0.40.3                 142MB
> local-ai-demo-web:1.0.0                     62.7MB
> local-ai-demo-backend:1.0.0                 158MB
> ```

### 4. Look at the containers and the one port

```bash
docker compose ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'
```

> **What it does:** Shows each running container, its health, and published ports.
> **Why:** A container port is only reachable from your machine if it is published. Here only
> `web` is.
> **Expected:**
>
> ```text
> SERVICE    STATUS                    PORTS
> backend    Up 2 minutes (healthy)
> ollama     Up 2 minutes (healthy)
> postgres   Up 2 minutes (healthy)
> web        Up 2 minutes (healthy)    127.0.0.1:3000->8080/tcp
> ```

Open <http://localhost:3000>. Then try the backend directly:

```bash
curl --max-time 3 http://127.0.0.1:8000/api/health; echo "exit code $?"
```

> **What it does:** Tries to reach the backend's port 8000 from your machine.
> **Why:** To see that an unpublished port is not reachable, even though the container listens on it.
> **Expected:** `exit code 7` (could not connect). The backend is only reachable through `web`.

### 5. Look at the volumes

```bash
docker volume ls --filter name=local-ai-demo
```

> **What it does:** Lists the named volumes.
> **Why:** These hold everything that must survive a container being deleted.
> **Expected:**
>
> ```text
> DRIVER    VOLUME NAME
> local     local-ai-demo-ollama-models
> local     local-ai-demo-postgres-data
> ```

### 6. Prove that data outlives containers

Open <http://localhost:3000/app/>, create a note, then:

```bash
docker compose down
docker compose up -d --wait
```

> **What it does:** `down` stops **and deletes** all four containers and both networks. `up`
> creates new ones from the same images.
> **Why:** Containers are disposable. Data is not, because it is in volumes, which `down` keeps.
> **Expected:** After `up`, refresh the page: your note is still there.

> [!WARNING]
> `docker compose down -v` also deletes the volumes: every note, and the downloaded model. Never add
> `-v` unless you mean it.

### 7. Run the smoke test

```bash
./scripts/smoke-test.sh
```

> **What it does:** Checks health, creates a note, asks the model about it, stops and recreates
> every container, checks the note survived, asks again, and deletes the test note.
> **Why:** One command that proves the whole stack works, including persistence.
> **Expected:** A list of `ok` lines, two real answers such as
> `answer: 'The spare key is in drawer 7. [#3]'`, and `smoke test passed`.

## Verification

- [ ] `docker compose ps` shows four healthy services and one published port
- [ ] `curl http://127.0.0.1:8000` fails, `http://localhost:3000` works
- [ ] A note survives `docker compose down` and `up`
- [ ] `./scripts/smoke-test.sh` passes

## Exercises

1. Run `docker compose stop ollama`, then ask a question in the assistant. Read the error the UI
   shows. Start it again with `docker compose start ollama`.
2. Change `WEB_PORT=3000` to `3100` in `.env` and run `docker compose up -d --wait`. Which
   container was recreated, and why only that one?
3. Run `docker inspect local-ai-demo-postgres-1 --format '{{json .Mounts}}'`. Where does the volume
   live on disk?

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Bind for 127.0.0.1:3000 failed: port is already allocated` | Something else uses port 3000 | Set `WEB_PORT=3100` in `.env` |
| `Set POSTGRES_PASSWORD in .env` | No `.env`, or the variable is empty | `cp .env.example .env`, set it |
| `dependency failed to start: ... ollama is unhealthy` | Ollama cannot read the model store | `./scripts/diagnose.sh`; see module 11 |
| `/api/ready` says `"model":"missing: qwen3:0.6b"` | The model was never pulled into the volume | `./scripts/pull-model.sh` |
| PostgreSQL logs `password authentication failed` | You changed `POSTGRES_PASSWORD` after the volume was created | Put the original password back; the password is stored in the data volume |

Next: [03 · Frontend to Backend over HTTP](03-frontend-to-backend.md)
