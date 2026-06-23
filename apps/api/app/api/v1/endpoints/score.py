from fastapi import APIRouter, HTTPException

from app.data.mock_report import build_mock_report
from app.schemas.score import NeighborhoodReport
from app.services.cache import get_lookup

router = APIRouter()


@router.get("/{address_id}", response_model=NeighborhoodReport)
async def get_score(address_id: str):
    lookup = await get_lookup(address_id)
    if lookup is None:
        raise HTTPException(status_code=404, detail="Address lookup not found")

    return build_mock_report(
        address_raw=lookup["address_raw"],
        address_normalized=lookup["address_normalized"],
        latitude=lookup["latitude"],
        longitude=lookup["longitude"],
        geoid=lookup.get("geoid") or "unknown",
    )
