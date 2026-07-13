"""Postgres-backed user store tests (requires Docker Compose `db` on localhost)."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.session import _async_database_url
from app.services.user_store import PostgresUserStore


def _fake_hash(pw: str) -> str:
    return f"hashed:{pw}"


@pytest_asyncio.fixture()
async def db_session():
    engine = create_async_engine(_async_database_url(settings.DATABASE_URL), pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"Postgres not available: {exc}")

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_retrieve_by_email(db_session: AsyncSession):
    store = PostgresUserStore(db_session)
    email = f"alice-{uuid.uuid4().hex[:8]}@example.com"
    user = await store.create(email, "Alice", _fake_hash("password123"))
    assert user.email == email.lower()
    assert user.tier == "free"

    found = await store.get_by_email(email)
    assert found is not None
    assert found.id == user.id

    # cleanup
    from app.models import User
    import uuid as uuid_mod

    row = await db_session.get(User, uuid_mod.UUID(user.id))
    if row:
        await db_session.delete(row)
        await db_session.commit()


@pytest.mark.asyncio
async def test_get_by_email_case_insensitive(db_session: AsyncSession):
    store = PostgresUserStore(db_session)
    email = f"Bob-{uuid.uuid4().hex[:8]}@Example.COM"
    user = await store.create(email, "Bob", _fake_hash("pw"))
    found = await store.get_by_email(email.lower())
    assert found is not None

    from app.models import User
    import uuid as uuid_mod

    row = await db_session.get(User, uuid_mod.UUID(user.id))
    if row:
        await db_session.delete(row)
        await db_session.commit()


@pytest.mark.asyncio
async def test_get_by_id(db_session: AsyncSession):
    store = PostgresUserStore(db_session)
    email = f"carol-{uuid.uuid4().hex[:8]}@example.com"
    user = await store.create(email, "Carol", _fake_hash("pw"))
    found = await store.get_by_id(user.id)
    assert found is not None
    assert found.email == email.lower()

    from app.models import User
    import uuid as uuid_mod

    row = await db_session.get(User, uuid_mod.UUID(user.id))
    if row:
        await db_session.delete(row)
        await db_session.commit()


@pytest.mark.asyncio
async def test_missing_user_returns_none(db_session: AsyncSession):
    store = PostgresUserStore(db_session)
    assert await store.get_by_email("nobody-missing@example.com") is None
    assert await store.get_by_id(str(uuid.uuid4())) is None
