from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app.schemas.lookup import LookupResponse
from app.services.cache import save_lookup
from app.services.geocoding import geocode_address, get_census_tract

router = APIRouter()


@router.get("", response_model=LookupResponse)
async def lookup_address(address: str = Query(..., min_length=3)):
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
