# 10 · Deploying on Bare-metal Linux without Internet

> ⏱ 30 minutes · Verify, load, restore, start and smoke test on a disconnected server.

> [!NOTE]
> **Advanced.** You need the bundle from module 09 and a Linux server, or the simulation in step 6.

## Goal

Move the bundle to a Linux server with no internet access and bring the stack up there, without a
single download, then prove it stores notes and answers questions.

## What you'll learn

- What the server must have before it goes offline (Docker Engine and Compose come from your OS)
- Verify before you trust: archive checksum, then every file
- `docker load` and image ID checks instead of `docker pull`
- Restoring a model into a volume and proving the runtime can load it
- Starting Compose so it cannot pull or build

## Architecture

```text
USB drive / private link          offline Linux server
  bundle.tar + bundle.tar.sha256 ─► sha256sum -c ─► tar -xf ─► ./scripts/offline-install.sh
                                     1 check-prereqs   2 verify-bundle   3 docker load (IDs checked)
                                     4 restore model (re-hash, read-only load test)
                                     5 .env (random password)   6 compose up --pull never --no-build
                                     then ./scripts/smoke-test.sh
```

## Prerequisites

### On the server, before it is disconnected

- Linux, x86_64 (or arm64 with an arm64 bundle)
- Docker Engine 24+ and the Docker Compose plugin 2.24+, installed from your distribution's
  packages (for a fully offline install, download the `.deb` or `.rpm` files on a connected
  machine first; see <https://docs.docker.com/engine/install/>)
- `bash`, `tar`, `gzip`, `sha256sum` (coreutils), `awk`, `sed`, `grep`; `curl` is optional
- 2+ CPU cores (4+ recommended), 4 GB+ memory (8 GB recommended), 4 GB+ free disk where Docker
  stores data, plus room for the 774 MB bundle
- Your user in the `docker` group, or use `sudo` for every command below

### Limitations

- CPU inference: about 70 to 80 tokens per second on the laptop used for these measurements;
  slower CPUs and CPUs without AVX2 are slower. The first answer after a start loads the model
  (2 to 10 seconds measured).
- One model, one inference at a time (`OLLAMA_NUM_PARALLEL=1`); other requests queue.
- No TLS and no login: put it behind your reverse proxy and network controls if more than one
  person uses it (see the README's security notes).

## Steps

### 1. Carry the two files

Copy `local-ai-demo-bundle-1.0.0-linux-amd64.tar` and its `.tar.sha256` to the server, for example
to `/opt/transfer/` from a USB drive.

### 2. Verify, then extract

```bash
cd /opt/transfer
sha256sum -c local-ai-demo-bundle-1.0.0-linux-amd64.tar.sha256
sudo tar -xf local-ai-demo-bundle-1.0.0-linux-amd64.tar -C /opt
sudo chown -R "$USER" /opt/local-ai-demo-bundle-1.0.0-linux-amd64
cd /opt/local-ai-demo-bundle-1.0.0-linux-amd64
```

> **What it does:** Checks the archive's SHA-256, extracts it to `/opt`, makes it yours, enters it.
> **Why:** Never extract an archive that fails its checksum.
> **Expected:** `local-ai-demo-bundle-1.0.0-linux-amd64.tar: OK`.

### 3. Disconnect

Unplug the network cable, disable the interface (`sudo ip link set <iface> down`), or block egress
at your firewall. From here on, nothing should need the internet. Keep a console or local session.

### 4. Install

```bash
./scripts/offline-install.sh
```

> **What it does:** Runs the six steps in the architecture above, then the smoke test.
> **Why:** One command a non-specialist can run, with a reason for every failure.
> **Expected (from a real run on a disconnected test server):**
>
> ```text
> ==> 3/6 Load images (docker load: no registry is contacted)
>   ok    local-ai-demo-backend:1.0.0 (sha256:a5cb27aa7245...)
>   ok    local-ai-demo-ollama:0.40.3 (sha256:a848a99d0362...)
>   ok    local-ai-demo-web:1.0.0 (sha256:72abd07554be...)
>   ok    postgres:18.6-alpine3.24 (sha256:c293117fcecd...)
> ==> 4/6 Restore the model
>   ok    qwen3:0.6b restored to local-ai-demo-ollama-models; 6 blobs re-hashed on disk
>   ok    Ollama loads qwen3:0.6b from the read-only volume with no network, as the stack will
> ==> 5/6 Configure (.env)
>   ok    created .env with a random POSTGRES_PASSWORD (kept in .../.env, mode 600)
> ==> 6/6 Start (--pull never --no-build)
> SERVICE    IMAGE                         STATUS
> backend    local-ai-demo-backend:1.0.0   Up 16 seconds (healthy)
> ollama     local-ai-demo-ollama:0.40.3   Up 22 seconds (healthy)
> postgres   postgres:18.6-alpine3.24      Up 22 seconds (healthy)
> web        local-ai-demo-web:1.0.0       Up 11 seconds (healthy)
> ```
>
> then the smoke test with real answers, and `Done. Open http://127.0.0.1:3000`.

> [!IMPORTANT]
> The installer never pulls. Before `compose up` it checks that every image Compose needs is
> already loaded and stops if one is missing, and it passes `--pull never --no-build`. The bundle
> has no `compose.override.yaml`, so there is no build step to fall back to either.

### 5. Serve your network

By default the UI listens on `127.0.0.1:3000`, on the server only. To serve other machines:

```bash
./scripts/offline-install.sh --bind 0.0.0.0 --skip-smoke
```

> **What it does:** Sets `WEB_BIND=0.0.0.0` in `.env` and recreates `web`. Images and data are kept.
> **Why:** Opening a port is a decision, not a default.
> **Expected:** Other machines can open `http://<server-address>:3000`. Restrict that port with
> your firewall to the networks that should use it.

### 6. No spare server? Simulate one

```bash
./scripts/airgap-simulate.sh
```

> **What it does:** On your connected machine, starts a fresh Docker-in-Docker "server" on a Docker
> network with `internal: true` (no route anywhere), copies the bundle in, and runs steps 2 and 4
> plus the air-gap test (module 11) inside it. Its Docker daemon starts with zero images.
> **Why:** It exercises every offline step with the network genuinely unavailable, on any machine
> with Docker. It is a simulation: the kernel, CPU and memory are your machine's.
> **Expected:** `PASSED with no internet on the host or in the containers`, then
> `the bundle installed and answered questions on a server with no internet`. About 2 minutes.

## Verification

- [ ] `sha256sum -c` printed `OK` before you extracted
- [ ] The installer loaded four images with IDs matching the manifest
- [ ] `docker compose ps` shows four healthy services
- [ ] The smoke test passed with the server disconnected

## Exercises

1. Run `./scripts/offline-install.sh` a second time. Which steps are skipped, and why is it safe to
   re-run?
2. Delete one image (`docker rmi local-ai-demo-web:1.0.0`) and run `docker compose up -d --pull never`.
   Read the error. Then let the installer put it back.
3. Look at `.env` (`cat .env`): which values did the installer set from the bundle's manifest?

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `bundle is linux/amd64, this machine is arm64` | Wrong bundle for this CPU | Build the bundle on (or for) the server's architecture |
| `the archive does not match its checksum` | Incomplete or altered copy | Copy it again; compare checksums on both ends |
| `image ... loaded with ID ..., the manifest says ...` | A different image with the same tag was already present, or the file is damaged | `docker rmi` that tag and re-run the installer |
| `Ollama cannot use the restored model read-only` | Damaged model files, or a bundle from an older script | Re-run the installer; if it repeats, rebuild the bundle |
| `Bind for 0.0.0.0:3000 failed` | Port 3000 in use on the server | Set `WEB_PORT` in `.env`, re-run the installer |
| Anything else | | `./scripts/diagnose.sh` |

Next: [11 · Acceptance Testing, Troubleshooting and Offline Updates](11-operations.md)
