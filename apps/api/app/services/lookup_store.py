"""Saved-lookup persistence — Postgres join behind LookupStore protocol."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import AddressLookup, SavedLookup as SavedLookupRow, User
from app.schemas.auth import SavedLookup


def _place_key(geoid: Optional[str], address_normalized: Optional[str]) -> str:
    geo = (geoid or "").strip()
    if geo:
        return f"geoid:{geo}"
    return f"addr:{(address_normalized or '').strip().lower()}"


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

    async def set_favorite(
        self, user_id: str, address_id: str, *, is_favorite: bool
    ) -> Optional[SavedLookup]: ...

    async def delete_for_user(self, user_id: str, address_id: str) -> str: ...

    async def touch(self, user_id: str, address_id: str) -> Optional[SavedLookup]: ...


class PostgresLookupStore:
    """List/save user lookups via address_lookups + saved_lookups."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_schema(
        self,
        row: SavedLookupRow,
        *,
        overall_score: Optional[float] = None,
    ) -> SavedLookup:
        addr = row.address_lookup
        activity = row.last_activity_at or row.created_at
        return SavedLookup(
            user_id=str(row.user_id),
            address_id=str(row.address_lookup_id),
            address_normalized=(
                (addr.address_normalized if addr and addr.address_normalized else None)
                or (addr.address_raw if addr else "")
                or row.label
                or ""
            ),
            looked_up_at=row.created_at.isoformat() if row.created_at else "",
            last_activity_at=activity.isoformat() if activity else "",
            is_favorite=bool(row.is_favorite),
            overall_score=overall_score,
        )

    async def _scores_by_geoid(self, geoids: list[str]) -> dict[str, float]:
        clean = [g for g in geoids if g]
        if not clean:
            return {}
        result = await self._session.execute(
            text(
                """
                SELECT geoid, overall_score
                FROM neighborhood_scores
                WHERE data_vintage = :vintage
                  AND geoid = ANY(:geoids)
                """
            ),
            {"vintage": settings.SCORE_DATA_VINTAGE, "geoids": clean},
        )
        out: dict[str, float] = {}
        for geoid, score in result.all():
            if geoid is not None and score is not None:
                out[str(geoid)] = float(score)
        return out

    async def merge_duplicate_saved_lookups(self, user_id: str) -> int:
        """Collapse saved rows that share the same place key. Returns deleted count."""
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return 0

        user = await self._session.get(User, uid)
        if user is None:
            return 0
        if user.lookups_deduped_at is not None:
            return 0

        stmt = (
            select(SavedLookupRow)
            .where(SavedLookupRow.user_id == uid)
            .options(selectinload(SavedLookupRow.address_lookup))
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        groups: dict[str, list[SavedLookupRow]] = {}
        for row in rows:
            addr = row.address_lookup
            key = _place_key(
                addr.geoid if addr else None,
                (addr.address_normalized if addr else None) or row.label,
            )
            groups.setdefault(key, []).append(row)

        deleted = 0
        for group in groups.values():
            if len(group) < 2:
                continue
            group.sort(
                key=lambda r: r.last_activity_at or r.created_at or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            survivor = group[0]
            survivor.is_favorite = any(r.is_favorite for r in group)
            for dup in group[1:]:
                await self._session.delete(dup)
                deleted += 1

        user.lookups_deduped_at = datetime.now(timezone.utc)
        await self._session.commit()
        return deleted

    async def list_for_user(self, user_id: str) -> list[SavedLookup]:
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return []

        await self.merge_duplicate_saved_lookups(user_id)

        stmt = (
            select(SavedLookupRow)
            .where(SavedLookupRow.user_id == uid)
            .options(selectinload(SavedLookupRow.address_lookup))
            .order_by(SavedLookupRow.last_activity_at.desc().nulls_last())
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        geoids = [
            (r.address_lookup.geoid if r.address_lookup and r.address_lookup.geoid else "")
            for r in rows
        ]
        scores = await self._scores_by_geoid(geoids)
        items: list[SavedLookup] = []
        for row in rows:
            geo = row.address_lookup.geoid if row.address_lookup else None
            items.append(
                self._to_schema(
                    row,
                    overall_score=scores.get(geo) if geo else None,
                )
            )
        return items

    async def _find_reusable_address(
        self,
        *,
        geoid: Optional[str],
        address_normalized: str,
    ) -> Optional[AddressLookup]:
        if geoid:
            result = await self._session.execute(
                select(AddressLookup)
                .where(AddressLookup.geoid == geoid)
                .order_by(AddressLookup.last_looked_up_at.desc())
                .limit(1)
            )
            found = result.scalar_one_or_none()
            if found is not None:
                return found
        result = await self._session.execute(
            select(AddressLookup)
            .where(AddressLookup.address_normalized == address_normalized)
            .order_by(AddressLookup.last_looked_up_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

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
        """Reuse address_lookups for same place; upsert saved_lookups with activity bump."""
        now = datetime.now(timezone.utc)
        addr = await self._find_reusable_address(
            geoid=geoid, address_normalized=address_normalized
        )
        if addr is None:
            addr = AddressLookup(
                address_raw=address_raw,
                address_normalized=address_normalized,
                latitude=latitude,
                longitude=longitude,
                geoid=geoid,
                last_looked_up_at=now,
            )
            self._session.add(addr)
            await self._session.flush()
        else:
            addr.address_raw = address_raw
            addr.address_normalized = address_normalized
            addr.latitude = latitude
            addr.longitude = longitude
            if geoid:
                addr.geoid = geoid
            addr.last_looked_up_at = now
            addr.lookup_count = (addr.lookup_count or 0) + 1
            await self._session.flush()

        if user_id:
            try:
                uid = uuid.UUID(user_id)
            except ValueError:
                uid = None
            if uid is not None:
                # Prefer an existing saved row for this place (same geoid / normalized).
                existing_place: Optional[SavedLookupRow] = None
                if geoid:
                    result = await self._session.execute(
                        select(SavedLookupRow)
                        .join(AddressLookup)
                        .where(
                            SavedLookupRow.user_id == uid,
                            AddressLookup.geoid == geoid,
                        )
                        .options(selectinload(SavedLookupRow.address_lookup))
                        .limit(1)
                    )
                    existing_place = result.scalar_one_or_none()
                if existing_place is None:
                    result = await self._session.execute(
                        select(SavedLookupRow)
                        .join(AddressLookup)
                        .where(
                            SavedLookupRow.user_id == uid,
                            AddressLookup.address_normalized == address_normalized,
                        )
                        .options(selectinload(SavedLookupRow.address_lookup))
                        .limit(1)
                    )
                    existing_place = result.scalar_one_or_none()

                if existing_place is not None:
                    existing_place.last_activity_at = now
                    existing_place.label = address_normalized
                    # Point at the canonical reused address row when different.
                    if existing_place.address_lookup_id != addr.id:
                        # Avoid unique conflicts if both ids somehow saved.
                        conflict = await self._session.execute(
                            select(SavedLookupRow).where(
                                SavedLookupRow.user_id == uid,
                                SavedLookupRow.address_lookup_id == addr.id,
                            )
                        )
                        other = conflict.scalar_one_or_none()
                        if other is not None and other.id != existing_place.id:
                            existing_place.is_favorite = (
                                existing_place.is_favorite or other.is_favorite
                            )
                            await self._session.delete(other)
                            await self._session.flush()
                        existing_place.address_lookup_id = addr.id
                    await self._session.commit()
                    await self._session.refresh(addr)
                    return str(addr.id)

                stmt = (
                    insert(SavedLookupRow)
                    .values(
                        user_id=uid,
                        address_lookup_id=addr.id,
                        label=address_normalized,
                        is_favorite=False,
                        last_activity_at=now,
                    )
                    .on_conflict_do_update(
                        index_elements=["user_id", "address_lookup_id"],
                        set_={
                            "last_activity_at": now,
                            "label": address_normalized,
                        },
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

    async def _get_owned_row(
        self, user_id: str, address_id: str
    ) -> Optional[SavedLookupRow]:
        try:
            uid = uuid.UUID(user_id)
            aid = uuid.UUID(address_id)
        except ValueError:
            return None
        result = await self._session.execute(
            select(SavedLookupRow)
            .where(
                SavedLookupRow.user_id == uid,
                SavedLookupRow.address_lookup_id == aid,
            )
            .options(selectinload(SavedLookupRow.address_lookup))
        )
        return result.scalar_one_or_none()

    async def set_favorite(
        self, user_id: str, address_id: str, *, is_favorite: bool
    ) -> Optional[SavedLookup]:
        row = await self._get_owned_row(user_id, address_id)
        if row is None:
            return None
        row.is_favorite = is_favorite
        await self._session.commit()
        await self._session.refresh(row)
        geo = row.address_lookup.geoid if row.address_lookup else None
        scores = await self._scores_by_geoid([geo] if geo else [])
        return self._to_schema(row, overall_score=scores.get(geo) if geo else None)

    async def delete_for_user(self, user_id: str, address_id: str) -> str:
        """Returns 'deleted' | 'not_found' | 'favorited'."""
        row = await self._get_owned_row(user_id, address_id)
        if row is None:
            return "not_found"
        if row.is_favorite:
            return "favorited"
        await self._session.delete(row)
        await self._session.commit()
        return "deleted"

    async def touch(self, user_id: str, address_id: str) -> Optional[SavedLookup]:
        row = await self._get_owned_row(user_id, address_id)
        if row is None:
            return None
        row.last_activity_at = datetime.now(timezone.utc)
        await self._session.commit()
        await self._session.refresh(row)
        geo = row.address_lookup.geoid if row.address_lookup else None
        scores = await self._scores_by_geoid([geo] if geo else [])
        return self._to_schema(row, overall_score=scores.get(geo) if geo else None)
