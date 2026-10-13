-- Notes, with a generated full-text search vector. The title weighs more than the body (A > B).
-- `to_tsvector('english', ...)` with a constant configuration is immutable, so it can be a
-- STORED generated column: PostgreSQL keeps it in step with every INSERT and UPDATE.
CREATE TABLE notes (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title       TEXT        NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200),
    body        TEXT        NOT NULL DEFAULT '' CHECK (char_length(body) <= 20000),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    search      TSVECTOR GENERATED ALWAYS AS (
                    setweight(to_tsvector('english', title), 'A') ||
                    setweight(to_tsvector('english', body), 'B')
                ) STORED
);

-- Retrieval: `search @@ query` uses this GIN index.
CREATE INDEX notes_search_idx ON notes USING GIN (search);
-- Listing: newest first, with id as the tie-breaker for stable pages.
CREATE INDEX notes_updated_at_idx ON notes (updated_at DESC, id DESC);
