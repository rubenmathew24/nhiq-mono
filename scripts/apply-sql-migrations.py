#!/usr/bin/env python3
"""Apply pending numbered SQL files under infra/sql/ with schema_migrations bookkeeping.

Usage:
  python scripts/apply-sql-migrations.py --database-url "$DATABASE_URL"
  python scripts/apply-sql-migrations.py --database-url "$DATABASE_URL" --sql-dir infra/sql

Exit 0 on success (including no pending). Non-zero on failure.
Does not truncate or wipe product data.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import psycopg
except ImportError as exc:  # pragma: no cover
    print(
        "error: psycopg is required. Install with: pip install 'psycopg[binary]>=3.1'",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQL_DIR = REPO_ROOT / "infra" / "sql"

CREATE_BOOKKEEPING = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def normalize_database_url(url: str) -> str:
    """Make SQLAlchemy/asyncpg-style URLs usable by psycopg."""
    u = url.strip()
    if u.startswith("postgresql+asyncpg://"):
        u = "postgresql://" + u[len("postgresql+asyncpg://") :]
    elif u.startswith("postgres+asyncpg://"):
        u = "postgresql://" + u[len("postgres+asyncpg://") :]
    # asyncpg uses ssl=require; psycopg prefers sslmode=require
    if "ssl=" in u and "sslmode=" not in u:
        u = re.sub(r"([?&])ssl=", r"\1sslmode=", u)
    return u


def list_migration_files(sql_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(sql_dir.glob("*.sql")):
        name = path.name
        if name == "init.sql" or name.startswith("seed_"):
            continue
        # Numbered migrations: 002_..., 009_..., etc.
        if re.match(r"^\d{3,}_.+\.sql$", name):
            files.append(path)
    return files


def iter_statements(sql_text: str):
    """Yield SQL statements (psycopg executes one at a time). Good enough for our numbered migrations."""
    buf: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                yield stmt
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        yield tail


def apply_migrations(database_url: str, sql_dir: Path) -> int:
    url = normalize_database_url(database_url)
    migrations = list_migration_files(sql_dir)
    if not sql_dir.is_dir():
        print(f"error: sql dir not found: {sql_dir}", file=sys.stderr)
        return 1

    applied = 0
    with psycopg.connect(url) as conn:
        conn.execute(CREATE_BOOKKEEPING)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT filename FROM schema_migrations")
            done = {row[0] for row in cur.fetchall()}

        for path in migrations:
            if path.name in done:
                print(f"skip (already applied): {path.name}")
                continue
            sql = path.read_text(encoding="utf-8")
            print(f"apply: {path.name}")
            try:
                with conn.transaction():
                    for stmt in iter_statements(sql):
                        conn.execute(stmt)
                    conn.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)",
                        (path.name,),
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"error applying {path.name}: {exc}", file=sys.stderr)
                return 1
            applied += 1
            print(f"ok: {path.name}")

    print(f"done: applied={applied} pending_checked={len(migrations)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply pending infra/sql migrations")
    parser.add_argument(
        "--database-url",
        required=True,
        help="Postgres URL (postgresql://…; ssl=require or sslmode=require OK)",
    )
    parser.add_argument(
        "--sql-dir",
        type=Path,
        default=DEFAULT_SQL_DIR,
        help="Directory containing numbered *.sql migrations",
    )
    args = parser.parse_args(argv)
    return apply_migrations(args.database_url, args.sql_dir)


if __name__ == "__main__":
    raise SystemExit(main())
