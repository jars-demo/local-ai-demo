# Third-party notices

This project's own code is MIT licensed (see `LICENSE`). The deployment bundle also contains
third-party software and model weights, each under its own license. Nothing here is modified except
where stated.

## Model: Qwen3 0.6B (`qwen3:0.6b`)

- **Authors:** the Qwen team, Alibaba Cloud. <https://github.com/QwenLM/Qwen3>
- **License:** Apache License 2.0. The license text ships with the model in Ollama's model store
  (the `application/vnd.ollama.image.license` layer listed in the model manifest).
- **Distribution:** the quantised GGUF build published by Ollama at
  <https://ollama.com/library/qwen3> (tag `0.6b`, Q4_K_M, 523 MB). Downloaded by
  `scripts/pull-model.sh` and verified by SHA-256; not modified.
- A small model: answers can be incomplete or wrong. Do not rely on it for decisions without
  checking the source notes it cites.

## Ollama 0.40.3

- **License:** MIT. <https://github.com/ollama/ollama>
- `local-ai-demo-ollama` is a CPU-only repackaging of the official `ollama/ollama:0.40.3` image:
  the `ollama` binary and the CPU libraries under `/usr/lib/ollama` are copied unchanged; the GPU
  libraries are left out. The bundled components' license files (llama.cpp, ggml, Go and others)
  are kept in `/usr/lib/ollama` inside the image.
- With `--with-gpu`, the official image is included unchanged. It contains NVIDIA CUDA libraries
  under NVIDIA's license terms.

## Base images and packages

| Image | License |
|---|---|
| `postgres:18.6-alpine3.24` | PostgreSQL License; Alpine Linux packages under their own licenses |
| `python:3.13.16-slim-trixie` (backend runtime) | PSF License; Debian packages under their own licenses |
| `nginxinc/nginx-unprivileged:1.31.6-alpine` (web runtime) | BSD-2-Clause (nginx); Alpine packages |
| `ubuntu:noble-20260917` (Ollama runtime base) | Ubuntu packages under their own licenses |

Python dependencies (FastAPI, Uvicorn, psycopg, httpx, Pydantic) are MIT, BSD or LGPL-3.0
(psycopg) licensed; exact versions are pinned in `backend/uv.lock`. JavaScript dependencies are
pinned in `frontend/package-lock.json` and are not shipped at runtime: the web image contains only
the static build output.
