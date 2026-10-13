# 03 · Frontend to Backend over HTTP

> ⏱ 20 minutes · Follow one click from the browser through nginx to FastAPI and back.

## Goal

Trace a request from the browser to the backend, read it in the logs, and explain why the browser
only ever talks to one origin.

## What you'll learn

- How a static Next.js site talks to an API it does not host
- What a reverse proxy does, and why it removes the need for CORS
- The API contract: methods, status codes and the error shape
- Request ids and structured logs

## Architecture

```text
browser                     web container (nginx :8080)              backend container (:8000)
GET /app/          ──────►  /usr/share/nginx/html/app/index.html
fetch POST /api/ask ─────►  location /api/ → proxy_pass http://backend:8000 ─► FastAPI route /api/ask
                    ◄─────  same response, plus security headers   ◄─────────  JSON
```

The site is a static export (`next build` with `output: 'export'`): HTML, CSS and JavaScript files.
No Node.js runs in production. The assistant page calls `fetch('/api/...')`, a path on the same
origin, and nginx forwards it.

## Prerequisites

Module 02, stack running.

## Steps

### 1. Read the frontend's API client

Open `frontend/src/lib/api.ts`. Every call is `fetch(`${API_URL}/api${path}`)` and `API_URL` is empty
in Docker. So the browser requests `/api/notes` from the same host and port that served the page.

### 2. Read the proxy rule

Open `frontend/nginx.conf`:

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;
set $backend http://backend:8000;

location /api/ {
    proxy_pass $backend;
    proxy_read_timeout 30s;
}
```

`backend` is a Compose service name. `127.0.0.11` is Docker's built-in DNS server (module 05).

### 3. Call the API the way the browser does

```bash
curl -s -i 'http://127.0.0.1:3000/api/notes?limit=1' | head -12
```

> **What it does:** Requests one note through nginx and prints the response headers.
> **Why:** This is exactly what the browser's `fetch` sends.
> **Expected:** `HTTP/1.1 200 OK`, `Server: nginx`, an `x-request-id` header from the backend, and
> security headers added by nginx: `X-Frame-Options: DENY`, and a `Content-Security-Policy` with
> `connect-src 'self'`, which forbids the page from calling any other host.

### 4. Create, read, update and delete

```bash
curl -s -X POST http://127.0.0.1:3000/api/notes \
  -H 'Content-Type: application/json' \
  -d '{"title":"Wi-Fi","body":"The guest network is called harbour-guest."}' -i | head -1
curl -s http://127.0.0.1:3000/api/notes/9999
curl -s -X POST http://127.0.0.1:3000/api/notes -H 'Content-Type: application/json' -d '{"title":""}'
```

> **What it does:** Creates a note, asks for one that does not exist, and sends an invalid one.
> **Why:** A good API says what went wrong with the right status code and one consistent shape.
> **Expected:**
>
> ```text
> HTTP/1.1 201 Created
> {"error":{"code":"NOTE_NOT_FOUND","message":"Note 9999 does not exist."}}
> {"error":{"code":"VALIDATION_FAILED","message":"The request is not valid.","fields":{"title":"String should have at least 1 character"}}}
> ```

The full contract is at <http://localhost:3000/api/docs> (Swagger UI, served by the backend
through the same proxy).

| Action | Method and path | Success |
|---|---|---|
| List notes | `GET /api/notes?limit=20&offset=0` | `200` with `data` and `meta` |
| Create | `POST /api/notes` | `201` and a `Location` header |
| Read | `GET /api/notes/{id}` | `200` |
| Update | `PATCH /api/notes/{id}` | `200` |
| Delete | `DELETE /api/notes/{id}` | `204` |
| Summarise | `POST /api/notes/{id}/summary` | `200` |
| Ask | `POST /api/ask` | `200` |
| Health / readiness | `GET /api/health`, `GET /api/ready` | `200`, or `503` when not ready |

### 5. Follow the request in the logs

```bash
docker compose logs backend --tail 5
```

> **What it does:** Shows the backend's last log lines.
> **Why:** Every request is one JSON line with its method, path, status, duration and request id.
> **Expected:** Lines like
> `{"level": "info", "service": "backend", "msg": "request completed", "request_id": "9aa2d4...", "method": "GET", "path": "/api/notes", "status": 200, "duration_ms": 3.1}`.
> The `request_id` matches the `x-request-id` header nginx returned. Note bodies and questions are
> never logged.

## Verification

- [ ] You can explain why the browser never needs the backend's address
- [ ] You saw `201`, `404` and `422` with the same error shape
- [ ] You matched an `x-request-id` header to a backend log line

## Exercises

1. In the browser, open the developer tools, Network tab, and ask a question in the assistant. Which
   URL is called? Which host?
2. Send `{"title":"x","pinned":true}` to `POST /api/notes`. Why does the API reject a field it does
   not know instead of ignoring it?
3. nginx limits `/api/ask` to a short burst per client (`limit_req` in `nginx.conf`). Send eight asks
   in a loop and find the `429`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `502 Bad Gateway` from nginx | The backend is not running or not healthy | `docker compose ps backend`, `docker compose logs backend` |
| `504 Gateway Time-out` on `/api/ask` | Inference took longer than nginx waits (200 s) | Smaller questions, a faster CPU, or raise `proxy_read_timeout` and `LLM_TIMEOUT_SECONDS` together |
| The assistant says `The backend is not reachable` | The page was opened from `npm run dev` without `NEXT_PUBLIC_API_URL` | Use <http://localhost:3000>, or set `NEXT_PUBLIC_API_URL=http://localhost:3000` for dev |
| `429 Too Many Requests` | nginx rate limit on AI endpoints | Wait a few seconds; it protects the CPU |

Next: [04 · Backend to PostgreSQL](04-backend-to-postgres.md)
