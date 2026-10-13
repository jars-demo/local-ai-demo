"""End-to-end checks, run INSIDE the backend container by smoke-test.sh:

    docker compose exec -T backend python - create < scripts/smoke_test.py
    docker compose exec -T backend python - verify <note-id> < scripts/smoke_test.py

It calls http://web:8080 (nginx) by its Docker DNS name, so every request takes the same path as a
browser's: nginx -> backend -> PostgreSQL / Ollama. Only the standard library is used, and the
target host needs nothing but Docker.
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://web:8080"
MARKER = "smoke-check"


def call(method: str, path: str, body: dict | None = None, timeout: float = 300) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw)
        except ValueError:
            return error.code, {"raw": raw.decode(errors="replace")[:200]}


def check(ok: bool, label: str, detail: str = "", fix: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}{(': ' + detail) if detail else ''}", flush=True)
    if not ok:
        if fix:
            print(f"        fix: {fix}", flush=True)
        sys.exit(1)


def ask(question: str, note_id: int) -> None:
    started = time.monotonic()
    status, body = call("POST", "/api/ask", {"question": question})
    wall = time.monotonic() - started
    error = body.get("error", {})
    check(
        status == 200,
        "POST /api/ask",
        f"HTTP {status} {error.get('code', '')}",
        error.get("hint", "./scripts/diagnose.sh"),
    )
    inference = body.get("inference") or {}
    ids = [source["id"] for source in body.get("sources", [])]
    check(body.get("retrieval") == "search" and note_id in ids, "retrieval found the note", f"sources {ids}")
    check(bool(inference.get("output_tokens")), "the local model generated an answer", inference.get("model", ""))
    print(f"        answer: {body['answer'][:160]!r}")
    print(
        f"        model {inference['model']}: total {inference['total_ms']} ms "
        f"(load {inference['load_ms']} ms), {inference['prompt_tokens']} tokens in, "
        f"{inference['output_tokens']} tokens out; request wall time {wall:.1f} s"
    )


def create() -> None:
    with urllib.request.urlopen(BASE + "/healthz", timeout=5) as response:
        check(response.status == 200, "web (nginx) serves")
    status, body = call("GET", "/api/ready", timeout=30)
    check(
        status == 200,
        "GET /api/ready",
        json.dumps(body.get("checks", body)),
        "a missing model: run ./scripts/offline-install.sh (offline) or ./scripts/pull-model.sh",
    )
    status, model = call("GET", "/api/model", timeout=30)
    check(status == 200 and model.get("installed"), "model installed", model.get("name", ""))
    print(
        f"        {model['name']} {model['parameter_size']} {model['quantization']}, "
        f"{model['size_bytes'] / 1e6:.0f} MB, Ollama {model['ollama_version']}"
    )

    stamp = time.strftime("%Y%m%d%H%M%S")
    status, note = call(
        "POST",
        "/api/notes",
        {
            "title": f"Smoke test {stamp}",
            "body": f"The {MARKER} code word is lighthouse-{stamp}. The spare key is in drawer 7.",
        },
    )
    check(status == 201, "POST /api/notes stored a note in PostgreSQL", f"id {note.get('id')}")
    ask("Where is the spare key?", note["id"])

    status, summary = call("POST", f"/api/notes/{note['id']}/summary")
    check(status == 200 and bool(summary.get("summary")), "POST /api/notes/{id}/summary")
    print(f"NOTE_ID={note['id']}")


def verify(note_id: int) -> None:
    status, note = call("GET", f"/api/notes/{note_id}", timeout=30)
    check(
        status == 200 and MARKER in note.get("body", ""),
        "the note survived the restart",
        f"id {note_id}",
        "check that the postgres-data volume was not removed (docker volume ls)",
    )
    ask("Where is the spare key?", note_id)
    status, _ = call("DELETE", f"/api/notes/{note_id}", timeout=30)
    check(status == 204, "cleaned up the test note")


if __name__ == "__main__":
    if sys.argv[1:2] == ["create"]:
        create()
    elif sys.argv[1:2] == ["verify"] and len(sys.argv) == 3:
        verify(int(sys.argv[2]))
    else:
        sys.exit("usage: smoke_test.py create | verify <note-id>")
