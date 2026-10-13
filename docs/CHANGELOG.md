# Changelog

All notable changes to this project will be documented in this file.
See [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) for format,
and [Semantic Versioning](https://semver.org/) for version numbers.

## [Unreleased]

### Added

- AI Notes Assistant: Next.js static site and assistant UI, FastAPI backend, PostgreSQL 18 with
  full-text retrieval, Ollama 0.40.3 serving `qwen3:0.6b` on the CPU. No external AI APIs.
- Docker Compose stack with an internal private network, a single published port, health checks,
  non-root read-only containers and a read-only model volume.
- CPU-only Ollama image built from the official one (142 MB instead of 5.57 GB); optional GPU
  override with the official image.
- Offline pipeline: `build-bundle.sh` (tests, images, model, manifest, SHA-256, reproducible
  archive), `verify-bundle.sh`, `offline-install.sh`, `smoke-test.sh`, `airgap-test.sh`,
  `diagnose.sh`, `check-prereqs.sh`, and `airgap-simulate.sh` for a Docker-in-Docker offline server.
- Workshop: eleven modules, from architecture to air-gapped operations.
- CI: backend lint and tests (unit and PostgreSQL integration), frontend lint, typecheck and builds,
  shellcheck, Compose validation, image builds, and an end-to-end offline bundle test.
