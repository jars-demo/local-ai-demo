# 05 · Docker DNS and Service Networking

> ⏱ 20 minutes · Why service names work, why localhost does not, and the internal network.

## Goal

Explain how containers find each other, why `localhost` inside a container means "this container",
and how an internal network removes internet access from the services that handle your data.

## What you'll learn

- Docker's embedded DNS server resolves Compose service names
- `localhost` is per container
- Two networks: `edge` (published) and `private` (`internal: true`)
- How to check what a container can and cannot reach

## Architecture

```text
            edge network (bridge)                 private network (bridge, internal: true)
host:3000 ──► web ─────────────────────────────────► web
                                                     backend ──► postgres
                                                             └─► ollama
                                                     no gateway: nothing here reaches the internet
```

`web` is attached to both networks, so it can receive your request on `edge` and forward it to
`backend` on `private`.

## Prerequisites

Module 04, stack running.

## Steps

### 1. Service names are DNS names

```bash
docker compose exec backend getent hosts postgres ollama web
```

> **What it does:** Asks the backend container's resolver for three names.
> **Why:** Docker runs a DNS server at `127.0.0.11` in every container on a user-defined network.
> It answers with the current address of each service on the networks you share.
> **Expected (addresses vary):**
>
> ```text
> 172.26.0.3      postgres
> 172.26.0.2      ollama
> 172.26.0.5      web
> ```

Addresses change when containers are recreated. Names do not. That is why `compose.yaml` says
`OLLAMA_URL: http://ollama:11434`, and nginx resolves `backend` at request time.

### 2. localhost is the container itself

```bash
docker compose exec backend python -c "import urllib.request as u; print(u.urlopen('http://localhost:11434/api/version', timeout=3).read())"
docker compose exec backend python -c "import urllib.request as u; print(u.urlopen('http://ollama:11434/api/version', timeout=3).read())"
```

> **What it does:** Calls Ollama's version endpoint twice from the backend: once via `localhost`,
> once via its service name.
> **Why:** Every container has its own network namespace. Inside `backend`, port 11434 on
> `localhost` is the backend container, where nothing listens.
> **Expected:** The first fails with `URLError: <urlopen error [Errno 111] Connection refused>`.
> The second prints `b'{"version":"0.40.3"}'`.

> [!IMPORTANT]
> Never use `localhost` (or `127.0.0.1`) for container-to-container traffic. It only ever works by
> accident, for example when everything runs on the host during development, and breaks in Docker.

### 3. The internal network

```bash
docker network inspect local-ai-demo_private --format '{{.Internal}}'
```

> **What it does:** Reads the `Internal` flag of the private network.
> **Why:** An internal network has no gateway: containers on it can talk to each other and to
> nothing else.
> **Expected:** `true`.

### 4. Prove it from inside

```bash
docker compose exec backend python -c "
import socket
for target in ['registry.ollama.ai', 'pypi.org']:
    try: socket.getaddrinfo(target, 443); print(target, 'resolves')
    except OSError as e: print(target, 'does not resolve:', e)
try: socket.create_connection(('1.1.1.1', 443), timeout=4); print('1.1.1.1:443 reachable')
except OSError as e: print('1.1.1.1:443 unreachable:', e)
"
```

> **What it does:** Tries a DNS lookup of two public names and a TCP connection to a public IP
> address, from inside the backend.
> **Why:** This is strict network isolation. It holds even though your laptop is online.
> **Expected:**
>
> ```text
> registry.ollama.ai does not resolve: [Errno -3] Temporary failure in name resolution
> pypi.org does not resolve: [Errno -3] Temporary failure in name resolution
> 1.1.1.1:443 unreachable: [Errno 101] Network is unreachable
> ```

The same is true for `ollama`: `docker compose exec ollama ollama pull qwen3:0.6b` fails. That is
why `./scripts/pull-model.sh` uses a separate, temporary container on Docker's default network.

### 5. What is published

```bash
docker compose port web 8080
docker compose port backend 8000 || echo "backend: not published"
```

> **What it does:** Asks Compose which host address maps to each container port.
> **Why:** Only published ports are reachable from outside Docker.
> **Expected:** `127.0.0.1:3000` for web, then `no port 8000/tcp for container local-ai-demo-backend-1` and
> `backend: not published`. The `127.0.0.1` means even
> other machines on your network cannot reach the site until you set `WEB_BIND=0.0.0.0`.

## Verification

- [ ] Service names resolve inside containers, and `localhost` does not reach another container
- [ ] `local-ai-demo_private` is internal
- [ ] Public DNS and TCP fail from inside `backend`

## Exercises

1. Run `docker compose exec web wget -qO- http://backend:8000/api/health`. Why does this work from
   `web` when the backend has no published port?
2. Could `web` reach the internet? Check which networks it is on with
   `docker inspect local-ai-demo-web-1 --format '{{json .NetworkSettings.Networks}}'`. What would
   you change if you wanted it isolated too, and what would stop working?
3. Change `OLLAMA_URL` to `http://localhost:11434` in `compose.yaml`, run
   `docker compose up -d --wait`, and open `/api/ready`. Change it back.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Name or service not known` for a service name | The two containers share no network | Put both services on the same network in `compose.yaml` |
| `Connection refused` to `localhost` from a container | `localhost` is the container itself | Use the service name |
| nginx `host not found in upstream "backend"` at startup | Static `proxy_pass http://backend` resolves once at start | Use `resolver 127.0.0.11` and a variable, as `nginx.conf` does |
| A container needs the internet at runtime | It is on `private`, which is internal by design | Do not add egress. Download on the build machine and ship it in the bundle |

Next: [06 · Running and Querying the Local LLM](06-local-llm.md)
