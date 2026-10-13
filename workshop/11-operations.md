# 11 · Acceptance Testing, Troubleshooting and Offline Updates

> ⏱ 25 minutes · Prove the offline claim, diagnose failures, update and roll back without internet.

> [!NOTE]
> **Advanced.** Runs on the server from module 10 (or the simulation).

## Goal

Hand the server over with evidence: a report that shows it has no internet, its containers have no
route out, and it still stores notes and answers questions. Then learn to diagnose it, update it and
roll it back, all without a network.

## What you'll learn

- An acceptance test with evidence you can keep
- Reading `diagnose.sh`, and the failures it knows how to explain
- Updating with a new bundle, keeping data; rolling back
- Backing up the notes

## Architecture

```text
airgap-test.sh
  Part 1  host:        no default route, public DNS fails, TCP to 1.1.1.1 / 8.8.8.8 fails
  Part 2  containers:  private network internal; DNS + TCP fail inside backend;
                       `ollama pull` fails; model store read-only
  Part 3  application: smoke test (note in PostgreSQL, real inference, full restart, persistence)
  → airgap-report-<UTC time>.log
```

## Prerequisites

Module 10.

## Steps

### 1. The acceptance test

With the server disconnected:

```bash
./scripts/airgap-test.sh --require-offline-host
```

> **What it does:** Proves three things in order and writes everything it prints to
> `airgap-report-<time>.log`. With `--require-offline-host` it fails if the host itself can still
> reach the internet.
> **Why:** "It works offline" is a claim; this is the evidence, in a file you can attach to a
> change ticket.
> **Expected (from the simulated offline server):**
>
> ```text
> ==> Part 1: this host
>   ..    no default route
>   ok    this host cannot resolve or reach public internet hosts
> ==> Part 2: containers on the private network
>   ok    network local-ai-demo_private is internal (no gateway to the outside)
>   ok    DNS lookup of registry.ollama.ai fails: Temporary failure in name resolution
>   ok    TCP 1.1.1.1:443 fails: Network is unreachable
>   ok    ollama pull fails (no route out, and the model store is mounted read-only)
>   ok    the model volume is read-only at runtime
> ==> Part 3: the application works under these conditions
>   ok    POST /api/notes stored a note in PostgreSQL: id 1
>         answer: 'The spare key is in drawer 7. [#1]'
>   ok    the note survived the restart: id 1
> ==> Result
>   ok    PASSED with no internet on the host or in the containers
> ```

Without `--require-offline-host` (for example on your laptop) Part 1 is reported but not required,
and the result says `PASSED for container isolation (the host itself was online)`.

> [!IMPORTANT]
> What has been verified, and how: this repository's CI and `./scripts/airgap-simulate.sh` run this
> test on a simulated server (Docker-in-Docker on an internal network). Running it on your own
> physical server, disconnected, is the step that turns the simulation into proof for your
> environment. Keep the report.

### 2. Diagnose

```bash
./scripts/diagnose.sh
```

> **What it does:** Read-only checks of versions, images, containers, volumes, readiness, Ollama's
> own view of the model store, recent log errors and resource use. Every problem comes with a
> `fix:` line.
> **Why:** One command to run before asking for help, and its output to attach.
> **Expected on a healthy server:** `ok    ollama list: qwen3:0.6b 522 MB` and
> `ok    no problems found`.

Failures it recognises:

| It reports | Meaning |
|---|---|
| `X is missing` (an image) | Not loaded; re-run `./scripts/offline-install.sh` |
| `the model is not installed` | The model volume is empty or holds another model |
| `ollama list fails: ...` | Ollama runs but cannot read its store; restore it again |
| `PostgreSQL rejects the password` | `.env` password differs from the one the data volume was created with |
| `X ran out of memory` | Raise `OLLAMA_MEMORY_LIMIT` or add RAM |
| `permission denied` | A volume created by another user |

### 3. Update offline

Build a new bundle (new `APP_VERSION` in `.env` on the build machine), carry it over, verify it,
extract it next to the old one, and run its installer:

```bash
cd /opt/local-ai-demo-bundle-1.1.0-linux-amd64
cp ../local-ai-demo-bundle-1.0.0-linux-amd64/.env .env
./scripts/offline-install.sh
```

> **What it does:** Loads the new images (unchanged ones are skipped by ID), restores the model if
> it changed, keeps your `.env` (and so your database password), sets `APP_VERSION` from the new
> manifest, and recreates the containers. Database migrations run when the new backend starts.
> **Why:** Both bundles use the same Compose project name and the same named volumes, so notes and
> the model carry over.
> **Expected:** The same output as a first install, with `keeping the existing .env`.

### 4. Roll back

```bash
cd /opt/local-ai-demo-bundle-1.0.0-linux-amd64
./scripts/offline-install.sh
```

> **What it does:** Re-installs the previous bundle's images and versions.
> **Why:** Keep the previous bundle on the server until the new one has passed its acceptance test.
> **Expected:** The old version running, with your notes.

> [!CAUTION]
> A rollback across a database migration needs the old schema. Before an update that adds a
> migration, back up (step 5). The migration runner can undo the latest migration with
> `docker compose exec backend python -m app.db.migrate down --yes`, but `down` may delete data.

### 5. Back up and restore notes

```bash
docker compose exec -T postgres pg_dump -U notes -d notes --clean --if-exists > notes-$(date +%F).sql
docker compose exec -T postgres psql -U notes -d notes < notes-2026-10-13.sql
```

> **What it does:** Dumps the notes database to a SQL file, then loads such a file back.
> **Why:** Volumes survive container changes, not disk failures or `down -v`.
> **Expected:** A `.sql` file containing `CREATE TABLE public.notes` and your rows; the restore
> prints `DROP TABLE`, `CREATE TABLE` and `COPY` lines.

The model needs no backup: it is in the bundle.

## Verification

- [ ] `airgap-report-*.log` says `PASSED with no internet on the host or in the containers`
- [ ] `./scripts/diagnose.sh` reports `no problems found`
- [ ] You can explain how an update keeps notes, and what a rollback needs

## Exercises

1. Break it on purpose: `docker compose stop ollama`, then run `./scripts/diagnose.sh`. Does it
   tell you what is wrong and what to run? Start it again.
2. Put a wrong `POSTGRES_PASSWORD` in `.env` and run `docker compose up -d`. Which service fails,
   and what does `diagnose.sh` say? Restore the right value.
3. Write a one-page handover for the server's owner: where the bundle lives, how to update, how to
   back up, where the acceptance report is.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Part 1 fails: `this host can still reach the internet` | The server is still connected | Disconnect it, or drop `--require-offline-host` if you only test container isolation |
| Part 2 fails: a name resolves inside `backend` | The private network is not internal (edited `compose.yaml`) | Restore `internal: true` |
| Part 3 fails | The stack itself | `./scripts/diagnose.sh` |
| After an update, old images fill the disk | Previous versions are kept | `docker image prune` after the new version is accepted, keeping the bundle files for rollback |

You have finished the workshop. The [offline deployment guide](../docs/offline-deployment.md) is the
short version of Part 2 for the person who runs the server.
