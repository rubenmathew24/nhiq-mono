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
            SavedLookup(
                user_id=user.id,
                address_lookup_id=addr_old.id,
                created_at=t0,
                last_activity_at=t0,
            ),
            SavedLookup(
                user_id=user.id,
                address_lookup_id=addr_new.id,
                created_at=t1,
                last_activity_at=t1,
            ),
            SavedLookup(
                user_id=other.id,
                address_lookup_id=addr_other.id,
                created_at=t1,
                last_activity_at=t1,
            ),
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


@pytest.mark.asyncio
async def test_record_lookup_reuses_place_and_bumps_activity(db_session: AsyncSession):
    user = User(
        email=f"reuse-{uuid.uuid4().hex[:8]}@example.com",
        full_name="R",
        password_hash="x",
        tier="free",
    )
    db_session.add(user)
    await db_session.commit()

    store = PostgresLookupStore(db_session)
    try:
        id1 = await store.record_lookup(
            address_raw="1 Main",
            address_normalized="1 Main St, Austin, Texas",
            latitude=30.0,
            longitude=-97.0,
            geoid="48021950100",
            user_id=str(user.id),
        )
        id2 = await store.record_lookup(
            address_raw="1 Main St",
            address_normalized="1 Main St, Austin, Texas",
            latitude=30.0,
            longitude=-97.0,
            geoid="48021950100",
            user_id=str(user.id),
        )
        assert id1 == id2
        items = await store.list_for_user(str(user.id))
        assert len(items) == 1
        assert items[0].address_id == id1
        fav = await store.set_favorite(str(user.id), id1, is_favorite=True)
        assert fav is not None and fav.is_favorite is True
        assert await store.delete_for_user(str(user.id), id1) == "favorited"
        await store.set_favorite(str(user.id), id1, is_favorite=False)
        assert await store.delete_for_user(str(user.id), id1) == "deleted"
        assert await store.list_for_user(str(user.id)) == []
    finally:
        await db_session.execute(delete(SavedLookup).where(SavedLookup.user_id == user.id))
        await db_session.execute(delete(User).where(User.id == user.id))
        await db_session.execute(delete(AddressLookup).where(AddressLookup.geoid == "48021950100"))
        await db_session.commit()


@pytest.mark.asyncio
async def test_merge_duplicate_saved_lookups(db_session: AsyncSession):
    user = User(
        email=f"merge-{uuid.uuid4().hex[:8]}@example.com",
        full_name="M",
        password_hash="x",
        tier="free",
    )
    a1 = AddressLookup(
        address_raw="A",
        address_normalized="Same Place",
        geoid="11001980000",
    )
    a2 = AddressLookup(
        address_raw="B",
        address_normalized="Same Place",
        geoid="11001980000",
    )
    db_session.add_all([user, a1, a2])
    await db_session.flush()
    t0 = datetime.now(timezone.utc) - timedelta(days=1)
    t1 = datetime.now(timezone.utc)
    db_session.add_all(
        [
            SavedLookup(
                user_id=user.id,
                address_lookup_id=a1.id,
                is_favorite=True,
                created_at=t0,
                last_activity_at=t0,
            ),
            SavedLookup(
                user_id=user.id,
                address_lookup_id=a2.id,
                is_favorite=False,
                created_at=t1,
                last_activity_at=t1,
            ),
        ]
    )
    await db_session.commit()

    store = PostgresLookupStore(db_session)
    try:
        items = await store.list_for_user(str(user.id))
        assert len(items) == 1
        assert items[0].is_favorite is True
    finally:
        await db_session.execute(delete(SavedLookup).where(SavedLookup.user_id == user.id))
        await db_session.execute(delete(User).where(User.id == user.id))
        await db_session.execute(delete(AddressLookup).where(AddressLookup.id.in_([a1.id, a2.id])))
        await db_session.commit()


@pytest.mark.asyncio
async def test_favorite_touch_and_delete_gate(db_session: AsyncSession):
    user = User(
        email=f"fav-{uuid.uuid4().hex[:8]}@example.com",
        full_name="F",
        password_hash="x",
        tier="free",
    )
    addr = AddressLookup(
        address_raw="9 Elm",
        address_normalized="9 Elm St",
        geoid="36061000100",
    )
    db_session.add_all([user, addr])
    await db_session.flush()
    now = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.add(
        SavedLookup(
            user_id=user.id,
            address_lookup_id=addr.id,
            is_favorite=False,
            created_at=now,
            last_activity_at=now,
        )
    )
    await db_session.commit()

    store = PostgresLookupStore(db_session)
    try:
        before = (await store.list_for_user(str(user.id)))[0]
        touched = await store.touch(str(user.id), str(addr.id))
        assert touched is not None
        assert touched.last_activity_at >= before.last_activity_at

        fav = await store.set_favorite(str(user.id), str(addr.id), is_favorite=True)
        assert fav is not None and fav.is_favorite is True
        assert await store.delete_for_user(str(user.id), str(addr.id)) == "favorited"

        await store.set_favorite(str(user.id), str(addr.id), is_favorite=False)
        assert await store.delete_for_user(str(user.id), str(addr.id)) == "deleted"
        assert await store.list_for_user(str(user.id)) == []
        assert await store.delete_for_user(str(user.id), str(addr.id)) == "not_found"
    finally:
        await db_session.execute(delete(SavedLookup).where(SavedLookup.user_id == user.id))
        await db_session.execute(delete(User).where(User.id == user.id))
        await db_session.execute(delete(AddressLookup).where(AddressLookup.id == addr.id))
        await db_session.commit()
