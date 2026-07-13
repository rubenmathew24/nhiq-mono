"""Saved-lookup persistence — Postgres join behind LookupStore protocol."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AddressLookup, SavedLookup as SavedLookupRow
from app.schemas.auth import SavedLookup


@runtime_checkable
class LookupStore(Protocol):
    async def list_for_user(self, user_id: str) -> list[SavedLookup]: ...

    async def record_lookup(
        self,
        *,
        address_raw: str,
        address_normalized: str,
        latitude: float,
        longitude: float,
        geoid: Optional[str],
        user_id: Optional[str] = None,
    ) -> str: ...

    async def get_address_payload(self, address_id: str) -> Optional[dict[str, Any]]: ...


class PostgresLookupStore:
    """List/save user lookups via address_lookups + saved_lookups."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: str) -> list[SavedLookup]:
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return []

        stmt = (
            select(SavedLookupRow)
            .where(SavedLookupRow.user_id == uid)
            .options(selectinload(SavedLookupRow.address_lookup))
            .order_by(SavedLookupRow.created_at.desc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        items: list[SavedLookup] = []
        for row in rows:
            addr = row.address_lookup
            items.append(
                SavedLookup(
                    user_id=str(row.user_id),
                    address_id=str(row.address_lookup_id),
                    address_normalized=(
                        (addr.address_normalized if addr and addr.address_normalized else None)
                        or (addr.address_raw if addr else "")
                        or row.label
                        or ""
                    ),
                    looked_up_at=row.created_at.isoformat() if row.created_at else "",
                )
            )
        return items

    async def record_lookup(
        self,
        *,
        address_raw: str,
        address_normalized: str,
        latitude: float,
        longitude: float,
        geoid: Optional[str],
        user_id: Optional[str] = None,
    ) -> str:
        """Insert address_lookups row; optionally attach saved_lookups for a user. Returns address id."""
        addr = AddressLookup(
            address_raw=address_raw,
            address_normalized=address_normalized,
            latitude=latitude,
            longitude=longitude,
            geoid=geoid,
            last_looked_up_at=datetime.now(timezone.utc),
        )
        self._session.add(addr)
        await self._session.flush()

        if user_id:
            try:
                uid = uuid.UUID(user_id)
            except ValueError:
                uid = None
            if uid is not None:
                stmt = (
                    insert(SavedLookupRow)
                    .values(
                        user_id=uid,
                        address_lookup_id=addr.id,
                        label=address_normalized,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["user_id", "address_lookup_id"],
                    )
                )
                await self._session.execute(stmt)

        await self._session.commit()
        await self._session.refresh(addr)
        return str(addr.id)

    async def get_address_payload(self, address_id: str) -> Optional[dict[str, Any]]:
        try:
            aid = uuid.UUID(address_id)
        except ValueError:
            return None
        row = await self._session.get(AddressLookup, aid)
        if row is None:
            return None
        return {
            "address_raw": row.address_raw,
            "address_normalized": row.address_normalized or row.address_raw,
            "latitude": float(row.latitude) if row.latitude is not None else 0.0,
            "longitude": float(row.longitude) if row.longitude is not None else 0.0,
            "geoid": row.geoid or "",
        }
