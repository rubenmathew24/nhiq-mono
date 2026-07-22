"""Fail CI if migrated schema is missing columns the lookup store / list API need."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parents[3]
SQL_DIR = REPO_ROOT / "infra" / "sql"


def _load_mig():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import apply_sql_migrations as mig  # noqa: E402

    return mig


def _async_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url.replace("sslmode=", "ssl=", 1) if "sslmode=" in url else url


@pytest.mark.asyncio
async def test_lookup_list_query_requires_favorite_columns():
    """Simulate the 009 failure mode: SELECT is_favorite must succeed after migrate."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")

    mig = _load_mig()
    assert mig.apply_migrations(url, SQL_DIR) == 0

    engine = create_async_engine(_async_url(url), pool_pre_ping=True)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with Session() as session:
            # Same columns LookupStore list enrichment depends on
            await session.execute(
                text(
                    """
                    SELECT is_favorite, last_activity_at
                    FROM saved_lookups
                    LIMIT 1
                    """
                )
            )
            await session.execute(
                text(
                    """
                    SELECT lookups_deduped_at FROM users LIMIT 1
                    """
                )
            )
    except Exception as exc:  # noqa: BLE001
        if "does not exist" in str(exc).lower() or "undefinedcolumn" in str(exc).lower().replace(
            " ", ""
        ):
            pytest.fail(f"schema drift: missing column required by lookups API: {exc}")
        if "could not connect" in str(exc).lower() or "connect" in str(exc).lower():
            pytest.skip(f"Postgres not available: {exc}")
        raise
    finally:
        await engine.dispose()
