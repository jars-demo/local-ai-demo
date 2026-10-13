"""NoteStore and migrations against a real PostgreSQL. Run with `pytest -m integration`.

Needs DATABASE_URL. With the stack running:

    docker compose --profile test run --rm backend-test
"""

import os

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg_pool import ConnectionPool

from app.db import migrate
from app.notes.repository import NoteStore

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def database_url() -> str:
    """DATABASE_URL, with its database created first if it does not exist yet (notes_test)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set")
    params = conninfo_to_dict(url)
    admin = make_conninfo(url, dbname="postgres")
    with psycopg.connect(admin, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (params["dbname"],)
        ).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(params["dbname"])))
    return url


@pytest.fixture
def store(database_url):
    with psycopg.connect(database_url, autocommit=True) as conn:
        migrate.upgrade(conn)
        conn.execute("TRUNCATE notes RESTART IDENTITY")
    pool = ConnectionPool(database_url, min_size=1, max_size=2, open=True)
    yield NoteStore(pool)
    pool.close()


def test_migrations_are_idempotent(database_url, store):
    with psycopg.connect(database_url, autocommit=True) as conn:
        assert migrate.upgrade(conn) == []


def test_create_then_get_round_trips_unicode(store):
    note = store.create("Café ☕", "Ünïcode body\nwith a newline")

    assert store.get(note.id).body == "Ünïcode body\nwith a newline"


def test_update_with_none_keeps_the_existing_value(store):
    note = store.create("title", "body")

    updated = store.update(note.id, None, "new body")

    assert (updated.title, updated.body) == ("title", "new body")


def test_update_moves_updated_at_forward(store):
    note = store.create("title", "body")

    updated = store.update(note.id, "renamed", None)

    assert updated.updated_at > note.updated_at


def test_search_matches_any_word_of_the_question_not_all(store):
    rack = store.create("Rack layout", "The backup server is in rack four.")
    store.create("Groceries", "Milk and eggs.")

    found = store.search("which rack holds the backup NAS?", 5)

    assert [n.id for n in found] == [rack.id]


def test_search_ranks_title_matches_above_body_matches(store):
    in_body = store.create("Misc", "remember the firewall change")
    in_title = store.create("Firewall change", "details later")

    found = store.search("firewall", 5)

    assert [n.id for n in found] == [in_title.id, in_body.id]


def test_search_stems_words_so_deploying_matches_deploy(store):
    note = store.create("Release", "We deploy on Fridays.")

    assert [n.id for n in store.search("When are we deploying?", 5)] == [note.id]


def test_search_with_only_stop_words_returns_nothing(store):
    store.create("Release", "We deploy on Fridays.")

    assert store.search("what is the", 5) == []


def test_search_treats_sql_metacharacters_as_text(store):
    store.create("Quotes", "it's a test")

    assert store.search("'; DROP TABLE notes; --", 5) == []
    assert store.page(10, 0)[1] == 1


def test_database_rejects_a_title_longer_than_200_characters(store):
    with pytest.raises(psycopg.errors.CheckViolation):
        store.create("x" * 201, "")


def test_list_pages_newest_first_and_counts_all(store):
    for i in range(3):
        store.create(f"note {i}", "")

    rows, total = store.page(2, 1)

    assert ([r.title for r in rows], total) == (["note 1", "note 0"], 3)


def test_delete_returns_false_for_a_missing_note(store):
    assert store.delete(12345) is False
