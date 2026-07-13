from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.mock_report import DEMO_LOOKUPS, build_mock_report
from app.db.session import get_db
from app.schemas.score import NeighborhoodReport
from app.services.cache import get_lookup
from app.services.lookup_store import PostgresLookupStore

router = APIRouter()


@router.get("/{address_id}", response_model=NeighborhoodReport)
async def get_score(
    address_id: str,
    session: AsyncSession = Depends(get_db),
):
    lookup = await get_lookup(address_id)
    if lookup is None:
        # Demo IDs in DEMO_LOOKUPS are not stored in Redis — serve mock report.
        lookup = DEMO_LOOKUPS.get(address_id)
    if lookup is None:
        # Persisted address_lookups (dashboard/history / authenticated search).
        store = PostgresLookupStore(session)
        lookup = await store.get_address_payload(address_id)
    if lookup is None:
        raise HTTPException(status_code=404, detail="Address lookup not found")

    return build_mock_report(
        address_raw=lookup["address_raw"],
        address_normalized=lookup["address_normalized"],
        latitude=lookup["latitude"],
        longitude=lookup["longitude"],
        geoid=lookup.get("geoid") or "unknown",
    )
