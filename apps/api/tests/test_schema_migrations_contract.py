"""Schema contract: columns required by current API after migrations."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SQL_DIR = REPO_ROOT / "infra" / "sql"


def _load_mig():
    from tests.migrate_loader import load_migrate_module

    return load_migrate_module()


@pytest.fixture(scope="module")
def pg_url():
    url = os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")
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


def test_schema_contract_dashboard_columns(pg_url: str):
    mig = _load_mig()
    import psycopg

    assert mig.apply_migrations(pg_url, SQL_DIR) == 0
    with psycopg.connect(mig.normalize_database_url(pg_url)) as conn:
        cols = {
            r[0]
            for r in conn.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'saved_lookups'
                  AND column_name IN ('is_favorite', 'last_activity_at')
                """
            ).fetchall()
        }
        user_cols = {
            r[0]
            for r in conn.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'lookups_deduped_at'
                """
            ).fetchall()
        }
    assert cols == {"is_favorite", "last_activity_at"}
    assert "lookups_deduped_at" in user_cols
