import json
import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app.schemas.lookup import LookupResponse
from app.services.cache import save_lookup
from app.services.geocoding import geocode_address, get_census_tract

router = APIRouter()

_DEBUG_LOG = Path(__file__).resolve().parents[6] / "debug-9a6fa9.log"


def _agent_log(
    *,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict,
) -> None:
    try:
        payload = {
            "sessionId": "9a6fa9",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with _DEBUG_LOG.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload) + "\n")
    except OSError:
        pass


@router.get("", response_model=LookupResponse)
async def lookup_address(address: str = Query(..., min_length=3)):
    _agent_log(
        hypothesis_id="A",
        location="lookup.py:lookup_address:entry",
        message="lookup endpoint hit",
        data={"addressLength": len(address.strip())},
    )

    try:
        geocoded = await geocode_address(address)
    except ValueError as exc:
        _agent_log(
            hypothesis_id="C",
            location="lookup.py:lookup_address:geocode_failed",
            message="geocode raised ValueError",
            data={"error": str(exc)},
        )
        raise HTTPException(
            status_code=422,
            detail="Could not find that U.S. address. Try a full street address.",
        ) from exc

    _agent_log(
        hypothesis_id="C",
        location="lookup.py:lookup_address:geocode_ok",
        message="geocode succeeded",
        data={
            "lat": geocoded["latitude"],
            "lng": geocoded["longitude"],
            "hasNormalized": bool(geocoded.get("address_normalized")),
        },
    )

    geoid: str | None = None
    try:
        geoid = await get_census_tract(
            geocoded["latitude"],
            geocoded["longitude"],
        )
    except ValueError:
        geoid = None

    address_id = str(uuid4())
    try:
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
    except Exception as exc:
        _agent_log(
            hypothesis_id="B",
            location="lookup.py:lookup_address:redis_failed",
            message="save_lookup failed",
            data={"errorType": type(exc).__name__, "error": str(exc)},
        )
        raise

    _agent_log(
        hypothesis_id="B",
        location="lookup.py:lookup_address:success",
        message="lookup completed",
        data={"addressId": address_id, "hasGeoid": geoid is not None},
    )

    return LookupResponse(
        address_id=address_id,
        status="ready",
        address_normalized=geocoded["address_normalized"],
        geoid=geoid,
    )
