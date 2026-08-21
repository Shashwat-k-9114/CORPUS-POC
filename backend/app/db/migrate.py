from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

from app.config import Settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def apply_migrations(database_url: str) -> list[str]:
    applied: list[str] = []
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        existing = {row[0] for row in connection.execute("SELECT version FROM schema_migrations").fetchall()}
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if migration.name in existing:
                continue
            with connection.transaction():
                connection.execute(migration.read_text(encoding="utf-8"))
                connection.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (migration.name,))
            applied.append(migration.name)
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Corpus PostgreSQL migrations.")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()
    settings = Settings.from_env()
    database_url = args.database_url or settings.database_url
    print(f"Applied migrations: {apply_migrations(database_url)}")


if __name__ == "__main__":
    main()
