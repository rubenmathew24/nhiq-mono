"""Postgres lookup store tests (requires Docker Compose `db`)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.session import _async_database_url
from app.models import AddressLookup, SavedLookup, User
from app.services.lookup_store import PostgresLookupStore


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
async def test_empty_lookups(db_session: AsyncSession):
    store = PostgresLookupStore(db_session)
    assert await store.list_for_user(str(uuid.uuid4())) == []


@pytest.mark.asyncio
async def test_seeded_lookups_filtered_and_sorted(db_session: AsyncSession):
    user = User(
        email=f"lookups-{uuid.uuid4().hex[:8]}@example.com",
        full_name="L",
        password_hash="x",
        tier="free",
    )
    other = User(
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        full_name="O",
        password_hash="x",
        tier="free",
    )
    addr_old = AddressLookup(address_raw="Old", address_normalized="Old St")
    addr_new = AddressLookup(address_raw="New", address_normalized="New St")
    addr_other = AddressLookup(address_raw="Other", address_normalized="Other St")
    db_session.add_all([user, other, addr_old, addr_new, addr_other])
    await db_session.flush()

    t0 = datetime.now(timezone.utc) - timedelta(days=2)
    t1 = datetime.now(timezone.utc)
    db_session.add_all(
        [
            SavedLookup(user_id=user.id, address_lookup_id=addr_old.id, created_at=t0),
            SavedLookup(user_id=user.id, address_lookup_id=addr_new.id, created_at=t1),
            SavedLookup(user_id=other.id, address_lookup_id=addr_other.id, created_at=t1),
        ]
    )
    await db_session.commit()

    try:
        store = PostgresLookupStore(db_session)
        results = await store.list_for_user(str(user.id))
        assert len(results) == 2
        assert results[0].address_id == str(addr_new.id)
        assert results[0].address_normalized == "New St"
        assert results[1].address_id == str(addr_old.id)
    finally:
        await db_session.execute(delete(SavedLookup).where(SavedLookup.user_id.in_([user.id, other.id])))
        await db_session.execute(delete(User).where(User.id.in_([user.id, other.id])))
        await db_session.execute(
            delete(AddressLookup).where(AddressLookup.id.in_([addr_old.id, addr_new.id, addr_other.id]))
        )
        await db_session.commit()
