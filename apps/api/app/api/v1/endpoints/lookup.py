from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.schemas.lookup import LookupResponse
from app.services.cache import save_lookup
from app.services.geocoding import geocode_address, get_census_tract
from app.services.lookup_store import PostgresLookupStore

router = APIRouter()
optional_bearer = HTTPBearer(auto_error=False)


@router.get("", response_model=LookupResponse)
async def lookup_address(
    address: str = Query(..., min_length=3),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
    session: AsyncSession = Depends(get_db),
):
    try:
        geocoded = await geocode_address(address)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not find that U.S. address. Try a full street address.",
        ) from exc

    geoid: str | None = None
    try:
        geoid = await get_census_tract(
            geocoded["latitude"],
            geocoded["longitude"],
        )
    except ValueError:
        geoid = None

    user_id: Optional[str] = None
    if credentials and credentials.credentials:
        user_id = decode_access_token(credentials.credentials)

    store = PostgresLookupStore(session)
    try:
        address_id = await store.record_lookup(
            address_raw=address.strip(),
            address_normalized=geocoded["address_normalized"],
            latitude=geocoded["latitude"],
            longitude=geocoded["longitude"],
            geoid=geoid,
            user_id=user_id,
        )
    except Exception:
        # DB write failed — still serve an ephemeral Redis-backed lookup id.
        address_id = str(uuid4())

    await save_lookup(
        address_id,
        {
            "address_raw": address.strip(),
            "address_normalized": geocoded["address_normalized"],
            "latitude": geocoded["latitude"],
            "longitude": geocoded["longitude"],
            "geoid": geoid or "",
        },
    )

    return LookupResponse(
        address_id=address_id,
        status="ready",
        address_normalized=geocoded["address_normalized"],
        geoid=geoid,
    )
