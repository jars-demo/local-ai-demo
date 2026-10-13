# 08 · Multi-stage Builds and Image Optimization

> ⏱ 25 minutes · From a 5.6 GB Ollama image to 142 MB, and why each stage exists.

## Goal

Read the three Dockerfiles, understand what each stage contributes, and measure what multi-stage
builds save. Every image you build here is an image you will carry to an offline server.

## What you'll learn

- Multi-stage builds: build tools stay in early stages, the runtime gets only what it runs
- Layer order and caching: dependencies before source
- Non-root users, pinned base images, `.dockerignore`
- How to inspect an image's size layer by layer

## Architecture

```text
backend/Dockerfile   uv ─► build (deps into .venv) ─► test (dev deps + tests)       python:3.13.16-slim
                                               └─────► runtime (.venv + app/) ──────► 158 MB, uid 10001
frontend/Dockerfile  deps (npm ci) ─► build (next build) ─► runtime (nginx + out/) ─► 62.7 MB, uid 101
ollama/Dockerfile    official (5.57 GB) ─► collect (CPU files) ─► runtime (ubuntu) ─► 142 MB, uid 10001
```

## Prerequisites

Module 02.

## Steps

### 1. Measure

```bash
docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}' | grep -E 'ollama|local-ai-demo-(web|backend)|python:3.13|node:22'
```

> **What it does:** Compares the images you run with the images they are built from.
> **Why:** Size is time to ship, disk on the server, and attack surface.
> **Expected (measured):**
>
> ```text
> ollama/ollama:0.40.3                        5.57GB
> python:3.13.16-slim-trixie                  118MB
> node:22.23.3-alpine                         167MB
> local-ai-demo-ollama:0.40.3                 142MB
> local-ai-demo-web:1.0.0                     62.7MB
> local-ai-demo-backend:1.0.0                 158MB
> ```
>
> `ollama/ollama` is only present if you pulled it (`./scripts/build-bundle.sh` does, as the source
> of the slim image).

### 2. The Ollama image: keep only what CPU inference needs

Open `ollama/Dockerfile`. The official image ships CUDA, MLX and Vulkan libraries for every GPU it
supports: about 4.8 GB of `/usr/lib/ollama`. CPU inference needs the `ollama` binary, the
`llama-server` runner and the `libggml-cpu-*` libraries (one per CPU generation; Ollama picks the
best one at runtime). The `collect` stage copies just those, and the build fails if the layout ever
changes:

```dockerfile
RUN mkdir -p /out/usr/lib/ollama /out/usr/bin \
 && cp -a /usr/bin/ollama /out/usr/bin/ \
 && find /usr/lib/ollama -mindepth 1 -maxdepth 1 \( -type f -o -type l \) ! -name include \
      -exec cp -a {} /out/usr/lib/ollama/ \; \
 && test -x /out/usr/lib/ollama/llama-server \
 && ls /out/usr/lib/ollama/libggml-cpu-*.so > /dev/null
```

```bash
docker history local-ai-demo-ollama:0.40.3 --format 'table {{.Size}}\t{{.CreatedBy}}' | head -10
```

> **What it does:** Shows each layer and its size.
> **Why:** To see where the bytes are.
> **Expected:** One `63.7MB` layer (`COPY /out/usr/ /usr/`), a `182kB` CA bundle, tiny metadata
> layers, and the Ubuntu base underneath (about 78 MB).

The trade-off: no GPU. `compose.gpu.yaml` switches back to the official image for NVIDIA hosts.

### 3. The backend image: dependencies before source

```bash
docker history local-ai-demo-backend:1.0.0 --format 'table {{.Size}}\t{{.CreatedBy}}' | head -8
```

> **What it does:** Shows the backend's top layers.
> **Why:** The order matters for rebuild speed and for what ships.
> **Expected:**
>
> ```text
> SIZE      CREATED BY
> 0B        CMD ["python" "-m" "app"]
> ...
> 99.7kB    COPY app/ ./app/ # buildkit
> 39.5MB    COPY /app/.venv /app/.venv # buildkit
> ```

The `.venv` (39.5 MB of FastAPI, Uvicorn, psycopg, httpx, Pydantic) is copied from the `build`
stage. `uv`, its cache, pytest and ruff never reach the runtime. Because `pyproject.toml` and
`uv.lock` are copied before the source, editing Python code reuses the dependency layer.

### 4. The web image: no Node.js at runtime

`frontend/Dockerfile` installs packages and runs `next build` in Node stages, then copies only
`out/` (static files) into `nginx-unprivileged`. The 470 npm packages used to build the site are
not in the image.

### 5. Check the hardening

```bash
docker compose exec backend sh -c 'id; touch /app/x'
docker compose exec ollama id
```

> **What it does:** Shows the user each container runs as, and tries to write into the app folder.
> **Why:** Every service runs as a non-root user, with a read-only root filesystem,
> `cap_drop: [ALL]` and `no-new-privileges` (see `x-hardening` in `compose.yaml`).
> **Expected:** `uid=10001(app) gid=10001(app) groups=10001(app)`, then
> `touch: cannot touch '/app/x': Read-only file system`; and `uid=10001(ollama)` for Ollama.

### 6. What never enters an image

`backend/.dockerignore` excludes `.venv`, caches and `.env`. The web build context is the repository
root, so the root `.dockerignore` is an allow-list: only `frontend/`, `workshop/` and `docs/` are
sent to the builder. Secrets, bundles and model files cannot leak into an image by accident.

## Verification

- [ ] You can name what each stage of each Dockerfile is for
- [ ] The slim Ollama image is under 150 MB and serves the model (module 06 proved it)
- [ ] All three application images run as non-root

## Exercises

1. Move `COPY app/ ./app/` above the `uv sync` line in `backend/Dockerfile`, change one line of
   Python, and rebuild twice. What happens to the build time, and why? Put it back.
2. Build only the test stage: `docker build --target test -t backend-test backend/`. Compare its size
   with the runtime image.
3. In `ollama/Dockerfile`, which check would fail if a future Ollama renamed `llama-server`? Why is
   failing the build better than a smaller image that does not work?

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Ollama logs `llama-server binary not found` | A slim image built without the runner | Use the `collect` stage as written; it checks for `llama-server` |
| Backend build re-downloads every package on each change | Source copied before dependencies | Copy `pyproject.toml` and `uv.lock` first, then `uv sync`, then the source |
| `npm ci` fails in the web build | `package-lock.json` out of date | Run `npm install` in `frontend/` and commit the lockfile |
| An image is much larger than expected | Something unexpected in the build context | Check `.dockerignore`, then `docker history <image>` |

Next: [09 · Packaging a Portable Offline Bundle](09-offline-bundle.md)
