"""A small, explicit migration runner: numbered `.up.sql` / `.down.sql` files in migrations/.

Applied versions are recorded in `schema_migrations`. A transaction-scoped advisory lock means two
backend replicas starting at once cannot apply the same migration twice.

    python -m app.db.migrate status
    python -m app.db.migrate up
    python -m app.db.migrate down --yes     # rolls back the latest migration (may delete data)
"""

import argparse
import logging
import sys
from pathlib import Path

import psycopg

log = logging.getLogger("app.migrate")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
LOCK_ID = 7_340_001  # any constant shared by every backend instance

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT        PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def available() -> list[str]:
    """Migration versions on disk, in order: ['0001_create_notes', ...]."""
    return sorted(p.name.removesuffix(".up.sql") for p in MIGRATIONS_DIR.glob("*.up.sql"))


def applied(conn: psycopg.Connection) -> list[str]:
    conn.execute(_CREATE_TABLE)
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    return [row[0] for row in rows]


def upgrade(conn: psycopg.Connection) -> list[str]:
    """Apply every pending migration in one transaction. Returns the versions applied."""
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
        done = set(applied(conn))
        pending = [v for v in available() if v not in done]
        for version in pending:
            conn.execute((MIGRATIONS_DIR / f"{version}.up.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            log.info("migration applied", extra={"version": version})
    return pending


def downgrade(conn: psycopg.Connection) -> str | None:
    """Roll back the most recent migration. Returns its version, or None if nothing is applied."""
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
        done = applied(conn)
        if not done:
            return None
        version = done[-1]
        conn.execute((MIGRATIONS_DIR / f"{version}.down.sql").read_text(encoding="utf-8"))
        conn.execute("DELETE FROM schema_migrations WHERE version = %s", (version,))
        log.info("migration rolled back", extra={"version": version})
    return version


def main(argv: list[str] | None = None) -> int:
    from app.core.config import Settings
    from app.core.logs import setup_logging

    parser = argparse.ArgumentParser(prog="python -m app.db.migrate")
    parser.add_argument("command", choices=["status", "up", "down"])
    parser.add_argument("--yes", action="store_true", help="confirm a destructive rollback")
    args = parser.parse_args(argv)
    setup_logging()

    with psycopg.connect(Settings.from_env().database_url, autocommit=True) as conn:
        if args.command == "status":
            done = set(applied(conn))
            for version in available():
                print(f"{'applied' if version in done else 'pending'}  {version}")
        elif args.command == "up":
            print(f"applied: {upgrade(conn) or 'nothing, already up to date'}")
        else:
            if not args.yes:
                print("Rolling back can delete data. Re-run with --yes to confirm.")
                return 2
            print(f"rolled back: {downgrade(conn) or 'nothing'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
