# 04 · Backend to PostgreSQL

> ⏱ 25 minutes · Connection pools, migrations, parameterised SQL and full-text retrieval.

## Goal

See how the backend stores notes, how the schema is created and versioned, and how the same
database finds the notes relevant to a question, which is the "retrieval" step before inference.

## What you'll learn

- A connection string built from parts, with the host `postgres` (a service name)
- Numbered up and down migrations, applied once, safely, at startup
- Parameterised SQL: why user text never becomes part of a query
- PostgreSQL full-text search: `tsvector`, `tsquery`, ranking and a GIN index

## Architecture

```text
backend                                   postgres (volume local-ai-demo-postgres-data)
app/config.py   host=postgres port=5432 ─►  database "notes", user "notes"
app/migrate.py  0001_create_notes.up.sql ─► table notes + schema_migrations
app/notes.py    psycopg pool, plain SQL  ─► SELECT / INSERT / UPDATE / DELETE / full-text search
```

## Prerequisites

Module 03, stack running.

## Steps

### 1. How the backend finds the database

`backend/app/config.py` builds the connection from environment variables that `compose.yaml` sets:
`POSTGRES_HOST: postgres`, `POSTGRES_DB: notes`, `POSTGRES_USER: notes` and the password from
`.env`. No address is hard-coded: `postgres` is resolved by Docker's DNS (module 05).

### 2. Migrations

```bash
docker compose exec postgres psql -U notes -d notes -c "SELECT version, applied_at FROM schema_migrations;"
```

> **What it does:** Shows which schema migrations the backend has applied.
> **Why:** The backend applies pending files from `backend/app/migrations/` at startup, inside one
> transaction, holding a PostgreSQL advisory lock so two backends cannot race. Each version is
> recorded once.
> **Expected:**
>
> ```text
>       version      |          applied_at
> -------------------+-------------------------------
>  0001_create_notes | 2026-10-13 12:44:26.366103+00
> ```

Every migration has an `up` and a `down` file. `python -m app.migrate down --yes` rolls back the
latest one, and refuses without `--yes`, because dropping a table deletes data.

### 3. The table

```bash
docker compose exec postgres psql -U notes -d notes -c '\d notes'
```

> **What it does:** Describes the `notes` table.
> **Why:** The database enforces the rules too, not only the API: title length, body length, and a
> generated search column.
> **Expected (abridged):** columns `id`, `title`, `body`, `created_at`, `updated_at`, and
> `search tsvector ... generated always as (setweight(to_tsvector('english', title), 'A') ||
> setweight(to_tsvector('english', body), 'B')) stored`; indexes `notes_pkey`,
> `notes_search_idx gin (search)`, `notes_updated_at_idx`; check constraints on title and body length.

### 4. Parameterised SQL

Open `backend/app/notes.py`. Every query passes values separately from the SQL text:

```python
cur.execute("SELECT id, title, body, created_at, updated_at FROM notes WHERE id = %s", (note_id,))
```

psycopg sends the query and the value to PostgreSQL separately, so a title such as
`'; DROP TABLE notes; --` is stored as text and never runs. The integration test
`test_search_treats_sql_metacharacters_as_text` proves it against a real database.

### 5. Retrieval with full-text search

```bash
docker compose exec postgres psql -U notes -d notes -c "SELECT plainto_tsquery('english', 'Where is the backup NAS?');"
```

> **What it does:** Turns a question into search terms.
> **Why:** Stop words (`where`, `is`, `the`) are dropped and words are stemmed (`deploying` becomes
> `deploy`).
> **Expected:**
>
> ```text
>  plainto_tsquery
> ------------------
>  'backup' & 'nas'
> ```

`&` means "all terms". A question rarely uses every word of the note it is about, so the backend
turns `&` into `|` (any term) and ranks the matches:

```bash
docker compose exec postgres psql -U notes -d notes -c "
SELECT id, title,
       ts_rank_cd(search, replace(plainto_tsquery('english', 'Where is the backup NAS?')::text, ' & ', ' | ')::tsquery) AS score
FROM notes
WHERE search @@ replace(plainto_tsquery('english', 'Where is the backup NAS?')::text, ' & ', ' | ')::tsquery
ORDER BY score DESC;"
```

> **What it does:** Runs the same retrieval query the backend runs for `/api/ask`.
> **Why:** This is the "R" in retrieval-augmented generation, done with the database you already
> have: no embeddings, no vector database.
> **Expected:** The notes that mention a backup or a NAS, best first, for example
> `1 | Server rack layout | 0.8` if you created that note.

### 6. The index

```bash
docker compose exec postgres psql -U notes -d notes -c "SET enable_seqscan = off; EXPLAIN SELECT id FROM notes WHERE search @@ 'backup | nas'::tsquery;"
```

> **What it does:** Shows how PostgreSQL would run the search. `enable_seqscan = off` hides the
> sequential scan PostgreSQL rightly prefers for a handful of rows.
> **Why:** To confirm the GIN index can serve the search when the table grows.
> **Expected:** `Bitmap Index Scan on notes_search_idx`.

### 7. Run the integration tests

```bash
docker compose --profile test run --rm --build backend-test
```

> **What it does:** Builds the backend's `test` image stage and runs every test, including the
> ones marked `integration`, against the running PostgreSQL, in a separate `notes_test` database.
> **Why:** The retrieval SQL is only proven by running it on real PostgreSQL.
> **Expected:** `47 passed`.

## Verification

- [ ] `schema_migrations` lists `0001_create_notes`
- [ ] You can explain why `'; DROP TABLE notes; --` in a title is harmless
- [ ] The retrieval query returns your note for a question that shares only some of its words
- [ ] `47 passed`

## Exercises

1. Ask the assistant `When are we deploying?` with a note that says `We deploy on Fridays`. Run
   `plainto_tsquery` on both phrases: why do they match?
2. Ask a question that shares no words with any note. Which notes does `/api/ask` use, and what does
   the `retrieval` field say? (Hint: `backend/app/assistant.py`.)
3. Write a migration `0002_add_pinned.up.sql` that adds `pinned BOOLEAN NOT NULL DEFAULT false`, and
   its `down` file. Restart the backend and check `schema_migrations`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `password authentication failed for user "notes"` | `.env` password differs from the one the volume was created with | Restore the original password. Changing it requires `ALTER USER` inside PostgreSQL |
| Backend restarts with `relation "notes" does not exist` in `/api/ready` | `MIGRATE_ON_START=false` and migrations never ran | `docker compose exec backend python -m app.migrate up` |
| `psql: error: connection to server on socket` | You ran `psql` on the host, not in the container | Use `docker compose exec postgres psql ...` |
| Integration tests skip | `DATABASE_URL` not set | Run them through the `backend-test` service, which sets it |

Next: [05 · Docker DNS and Service Networking](05-docker-networking.md)
