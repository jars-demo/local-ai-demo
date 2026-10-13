# Offline deployment guide

This is the guide for the person who runs the server. It ships as `README.md` inside every bundle,
so it is there when the internet is not. The full teaching version is workshop modules 09 to 11.

## What you have

One archive, `local-ai-demo-bundle-<version>-linux-<arch>.tar`, and its `.tar.sha256`. Together
they contain everything the AI Notes Assistant needs: four container images, the language model
(`qwen3:0.6b`, Apache 2.0), the Compose file, scripts and this guide. Nothing is downloaded during
installation or while the application runs.

| In the bundle | Size (1.0.0, linux/amd64) |
|---|---|
| `images/local-ai-demo-web_1.0.0.tar.gz` (nginx, the site and API proxy) | 25.4 MB |
| `images/local-ai-demo-backend_1.0.0.tar.gz` (FastAPI) | 54.9 MB |
| `images/local-ai-demo-ollama_0.40.3.tar.gz` (Ollama, CPU-only) | 54.2 MB |
| `images/postgres_18.6-alpine3.24.tar.gz` | 116.5 MB |
| `models/qwen3_0.6b.tar` | 522.7 MB |
| Archive total | 774.0 MB |

`manifest.json` lists every artifact with its version, architecture, size and SHA-256.
`SHA256SUMS` has one line per file. No embedding model is needed: the app searches notes with
PostgreSQL full-text search.

## What "offline" means here

| Claim | Status after installation |
|---|---|
| **No external AI APIs** | Always. Answers come from the model in the `ollama` container. No API keys exist. |
| **No internet at runtime** | Yes. Images are loaded from files, the model is restored from a file, Compose runs with `--pull never --no-build`. |
| **Strict network isolation** | Yes. `backend`, `postgres` and `ollama` are on a Docker network with `internal: true`: they have no route out, even if the server does. The model store is mounted read-only. |

## Server requirements

| | Minimum | Recommended | Measured |
|---|---|---|---|
| OS | Linux, kernel with cgroups (any current distribution) | | |
| Architecture | Must match the bundle (`linux/amd64` or `linux/arm64`) | amd64 (tested) | |
| Docker | Engine 24+, Compose plugin 2.24+ | | Tested: 28.2.2 and 28.5.2 |
| CPU | 2 cores | 4+ cores with AVX2 | About 70 to 80 tokens/s on a 4-CPU laptop VM |
| Memory | 4 GB | 8 GB | Whole stack about 1.2 GB with the model loaded |
| Disk | 4 GB free where Docker stores data | 8 GB | Images and model about 1.2 GB, plus the bundle |
| GPU | Not needed | Optional, NVIDIA only (`--with-gpu` bundle) | |
| Tools | `bash`, `tar`, `gzip`, `sha256sum`, `awk`, `sed`, `grep` | `curl` | |

Install Docker Engine and the Compose plugin **before** the server goes offline, from your
distribution's packages (or packages downloaded on another machine). This bundle does not install
Docker.

Tested so far: Docker Desktop (WSL 2) and a simulated offline server (Docker-in-Docker on an
internal network, `./scripts/airgap-simulate.sh`). Not yet tested on physical hardware by this
project: run the acceptance test below on yours and keep the report.

## Install

```bash
# 1. Verify the archive before anything else.
sha256sum -c local-ai-demo-bundle-1.0.0-linux-amd64.tar.sha256

# 2. Extract and enter it.
sudo tar -xf local-ai-demo-bundle-1.0.0-linux-amd64.tar -C /opt
sudo chown -R "$USER" /opt/local-ai-demo-bundle-1.0.0-linux-amd64
cd /opt/local-ai-demo-bundle-1.0.0-linux-amd64

# 3. Install. Add --bind 0.0.0.0 to serve other machines (then restrict port 3000 at your firewall).
./scripts/offline-install.sh
```

`offline-install.sh`:

1. checks prerequisites (`scripts/check-prereqs.sh`);
2. verifies every file against `SHA256SUMS` and `manifest.json` (`scripts/verify-bundle.sh`);
3. `docker load`s each image and checks its ID against the manifest;
4. restores the model into the volume `local-ai-demo-ollama-models`, re-hashes every blob, and
   starts a throwaway Ollama with the volume read-only and no network to prove it loads;
5. creates `.env` with a random database password (mode 600) on first install, or keeps yours;
6. starts the stack with `docker compose up -d --pull never --no-build --wait`;
7. runs the smoke test: a note is stored, the model answers a question about it, every container is
   destroyed and recreated, and the note and the answer survive.

Then open `http://127.0.0.1:3000` on the server (or `http://<server>:3000` with `--bind 0.0.0.0`).

## Acceptance test

Disconnect the server (unplug it, `sudo ip link set <iface> down`, or block egress), then:

```bash
./scripts/airgap-test.sh --require-offline-host
```

It fails unless: the host cannot resolve or reach public addresses; the private Docker network is
internal; DNS and TCP fail from inside the backend; `ollama pull` fails; the model store is
read-only; and the smoke test passes. The output is saved to `airgap-report-<UTC time>.log`.

## Operate

| Task | Command |
|---|---|
| Status | `docker compose ps` |
| Logs | `docker compose logs --tail 100 backend` (JSON lines) |
| Diagnose a problem | `./scripts/diagnose.sh` (read-only; every problem has a `fix:` line) |
| Stop, keeping data | `docker compose down` |
| Start | `docker compose up -d --pull never --no-build --wait` |
| Back up notes | `docker compose exec -T postgres pg_dump -U notes -d notes --clean --if-exists > notes-$(date +%F).sql` |
| Restore notes | `docker compose exec -T postgres psql -U notes -d notes < notes-YYYY-MM-DD.sql` |
| Re-run the smoke test | `./scripts/smoke-test.sh` |

> [!CAUTION]
> `docker compose down -v` deletes the volumes: every note and the model. Restore the model by
> re-running `./scripts/offline-install.sh`; restore notes only from a backup.

## Update and roll back

1. On the build machine: raise `APP_VERSION`, run `./scripts/build-bundle.sh`.
2. Carry the new archive and `.sha256`; verify; extract next to the current bundle.
3. Copy the current `.env` into the new bundle directory, then run its `./scripts/offline-install.sh`.
   Images with unchanged IDs are skipped; notes and the model volume are kept; migrations run on start.
4. Run the acceptance test again.

To roll back, run the previous bundle's `./scripts/offline-install.sh`. Back up the notes before any
update that changes the database schema.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `sha256sum: WARNING: 1 computed checksum did NOT match` | The copy is damaged. Copy it again. Do not install it. |
| `bundle is linux/amd64, this machine is arm64` | Build a bundle for this architecture. |
| `the Docker daemon is not reachable` | `sudo systemctl start docker`; add your user to the `docker` group or use `sudo`. |
| `the Docker Compose v2 plugin is missing` | Install `docker-compose-plugin` from your OS packages. |
| `image ... is not loaded and will not be pulled` | Re-run `./scripts/offline-install.sh`; it loads images from `images/`. |
| `ollama is unhealthy` or `ollama list fails` | Re-run the installer (it restores and tests the model store). |
| `PostgreSQL rejects the password` | `.env` must keep the password the data volume was created with. |
| `Bind for ...:3000 failed: port is already allocated` | Set `WEB_PORT` in `.env`, re-run the installer. |
| The first answer takes 10 seconds | Normal: the model loads into memory once, then stays for 30 minutes. |
| `LLM_TIMEOUT` on a slow CPU | Raise `LLM_TIMEOUT_SECONDS` in `.env` (and expect slow answers). |

## Security notes

- There is **no login** and **no TLS**. Keep `WEB_BIND=127.0.0.1` for single-user use, or put the
  server behind your reverse proxy (TLS, authentication) and firewall.
- The database password lives only in `.env` (mode 600) and inside the data volume.
- Every container runs as a non-root user with a read-only root filesystem, no Linux capabilities
  and `no-new-privileges`. Only `web` publishes a port.
- A 0.6B-parameter model can be wrong. Answers cite the notes they used; check them.

Licenses: `LICENSE` (this project, MIT) and `THIRD-PARTY-NOTICES.md` (the model, Ollama, images).
