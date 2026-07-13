"""Shared FastAPI dependencies (DB session, auth service, lookup store)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth_service import AuthService
from app.services.lookup_store import LookupStore, PostgresLookupStore
from app.services.user_store import PostgresUserStore


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(PostgresUserStore(session))


def get_lookup_store(session: AsyncSession = Depends(get_db)) -> LookupStore:
    return PostgresLookupStore(session)
