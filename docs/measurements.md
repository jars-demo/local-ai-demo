# Measurements

Every number this project publishes (README, site, workshop) comes from this page, and every number
here was measured, with the command that produced it. When an image, the model or a version changes,
re-measure and update this page, `frontend/src/lib/measurements.ts` and the README together.

**Machine:** Windows 11 laptop, Docker Desktop 28.2.2, WSL 2 Linux VM (kernel 5.15, linux/amd64,
overlay2 storage), 4 CPUs and 7.8 GiB memory given to Docker, AVX2 available.
**Date:** 2026-10-13. **Version:** 1.0.0.

A dedicated Linux server will give different numbers, mainly model load time (disk speed) and
tokens per second (CPU).

## Images

```bash
docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}'
```

| Image | Unpacked | In the bundle (gzip) |
|---|---|---|
| `local-ai-demo-web:1.0.0` | 62.7 MB | 25.4 MB |
| `local-ai-demo-backend:1.0.0` | 158 MB | 54.9 MB |
| `local-ai-demo-ollama:0.40.3` | 142 MB | 54.2 MB |
| `postgres:18.6-alpine3.24` | 304 MB | 116.5 MB |
| `ollama/ollama:0.40.3` (official, for comparison and GPU) | 5.57 GB | not included by default |

## Model

| | |
|---|---|
| `qwen3:0.6b` on disk | 522,640,096 bytes of weights, 523 MB with its other blobs (`ollama list`: 522 MB) |
| Parameters, quantisation | 751.63M, Q4_K_M (`ollama show qwen3:0.6b`) |
| Loaded in memory | 1.0 GB (`ollama ps`) |
| In the bundle | 522.7 MB (`models/qwen3_0.6b.tar`, not compressed: GGUF does not compress) |

## Bundle

```bash
./scripts/build-bundle.sh --skip-tests
```

| | |
|---|---|
| Archive | 774.0 MB (`local-ai-demo-bundle-1.0.0-linux-amd64.tar`) |
| Build time, images already built | 1 min 22 s |
| Reproducibility | Two consecutive builds: identical SHA-256 (`4c10e30c...fca9`) |

## Memory

Sampled every two seconds with `docker stats --no-stream` while `./scripts/smoke-test.sh` ran:

| Container | Idle (model not loaded) | Model loaded |
|---|---|---|
| ollama | 78 MiB | 1.11 GiB |
| backend | 60 MiB | 60 to 74 MiB |
| postgres | 38 MiB | 38 MiB |
| web | 5.5 MiB | 5.5 MiB |
| **Total** | **about 180 MiB** | **about 1.2 GiB** |

Compose limits: web 64 MiB, backend 256 MiB, postgres 256 MiB, ollama 3 GiB (`OLLAMA_MEMORY_LIMIT`).

## Inference

From Ollama's own timings, as returned in every `/api/ask` response:

| Situation | Total | Of which model load |
|---|---|---|
| First request after the stack starts | 9.7 to 11.1 s | 9.7 to 10.4 s |
| First request after a restart on the simulated offline server | 2.4 to 4.0 s | 1.8 to 3.1 s |
| Model already loaded, short question | 0.2 to 2.6 s | under 20 ms |
| Generation speed | about 72 to 80 tokens/s | |

## Answer quality (small, workshop-specific)

Twenty questions over five short notes, checked by keyword, temperature 0.2, two seeds (scripts not
included; the method is in module 06):

| Model | Correct | Cited a note id |
|---|---|---|
| `qwen3:0.6b`, thinking off | 18 / 20 | 14 / 20 |
| `qwen2.5:0.5b` | 17 / 20 | 1 / 20 |

Then 33 questions comparing two prompts and two sampling settings for `qwen3:0.6b`: the shipped
prompt at temperature 0.2 scored 28 / 33 correct, 25 / 33 cited. This is a sanity check of this app,
not a benchmark of the models.
