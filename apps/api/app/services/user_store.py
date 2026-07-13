"""User persistence — Postgres implementation behind UserStore protocol."""

from __future__ import annotations

import uuid
from typing import Optional, Protocol, runtime_checkable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.auth import UserInDB


@runtime_checkable
class UserStore(Protocol):
    async def get_by_email(self, email: str) -> Optional[UserInDB]: ...
    async def get_by_id(self, user_id: str) -> Optional[UserInDB]: ...
    async def create(self, email: str, full_name: str, password_hash: str) -> UserInDB: ...


def _to_schema(row: User) -> UserInDB:
    return UserInDB(
        id=str(row.id),
        email=row.email,
        full_name=row.full_name or "",
        tier=row.tier or "free",  # type: ignore[arg-type]
        password_hash=row.password_hash or "",
        created_at=row.created_at.isoformat() if row.created_at else "",
    )


class PostgresUserStore:
    """Postgres-backed user repository (Docker Compose `db` / DATABASE_URL)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        stmt = select(User).where(func.lower(User.email) == email.lower())
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _to_schema(row) if row else None

    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return None
        row = await self._session.get(User, uid)
        return _to_schema(row) if row else None

    async def create(self, email: str, full_name: str, password_hash: str) -> UserInDB:
        row = User(
            email=email.lower(),
            full_name=full_name,
            password_hash=password_hash,
            tier="free",
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_schema(row)
