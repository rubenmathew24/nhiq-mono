"""Tests for scripts/apply-sql-migrations.py."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER = REPO_ROOT / "scripts" / "apply-sql-migrations.py"
SQL_DIR = REPO_ROOT / "infra" / "sql"


def _load_mig():
    from tests.migrate_loader import load_migrate_module

    return load_migrate_module()


def _database_url() -> str | None:
    return os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="module")
def pg_url():
    url = _database_url()
    if not url:
        pytest.skip("DATABASE_URL not set")
    mig = _load_mig()
    try:
        import psycopg
    except ImportError:
        pytest.skip("psycopg not installed")
    try:
        with psycopg.connect(mig.normalize_database_url(url)) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres not available: {exc}")
    return url


def test_apply_migrations_twice_is_noop(pg_url: str):
    mig = _load_mig()
    assert mig.apply_migrations(pg_url, SQL_DIR) == 0
    assert mig.apply_migrations(pg_url, SQL_DIR) == 0

    import psycopg

    with psycopg.connect(mig.normalize_database_url(pg_url)) as conn:
        names = [
            r[0]
            for r in conn.execute(
                "SELECT filename FROM schema_migrations ORDER BY filename"
            ).fetchall()
        ]
    assert any(n.startswith("009_") for n in names)


def test_bad_sql_fails_without_recording(pg_url: str, tmp_path: Path):
    mig = _load_mig()
    import psycopg

    bad = tmp_path / "999_bad_migration_test.sql"
    bad.write_text("THIS IS NOT VALID SQL;", encoding="utf-8")
    assert mig.apply_migrations(pg_url, tmp_path) != 0

    with psycopg.connect(mig.normalize_database_url(pg_url)) as conn:
        row = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE filename = %s",
            (bad.name,),
        ).fetchone()
    assert row is None


def test_cli_subprocess(pg_url: str):
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--database-url", pg_url, "--sql-dir", str(SQL_DIR)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 2 and "psycopg" in (proc.stderr or ""):
        pytest.skip("psycopg not installed for CLI")
    assert proc.returncode == 0, proc.stderr
