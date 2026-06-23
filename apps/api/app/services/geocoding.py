import json
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings

_DEBUG_LOG = Path(__file__).resolve().parents[4] / "debug-9a6fa9.log"


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


async def geocode_address(address: str) -> dict:
    """
    Returns {latitude, longitude, address_normalized} using Mapbox Geocoding API.
    Raises ValueError if address cannot be geocoded.
    """
    if not settings.MAPBOX_TOKEN:
        _agent_log(
            hypothesis_id="C",
            location="geocoding.py:geocode_address:no_token",
            message="MAPBOX_TOKEN missing",
            data={},
        )
        raise ValueError("Mapbox token is not configured")

    encoded = quote(address.strip(), safe="")
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded}.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params={
                "access_token": settings.MAPBOX_TOKEN,
                "country": "US",
                "types": "address",
                "limit": 1,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

    feature_count = len(data.get("features") or [])
    _agent_log(
        hypothesis_id="D",
        location="geocoding.py:geocode_address:mapbox_response",
        message="mapbox geocode response",
        data={"featureCount": feature_count, "statusCode": response.status_code},
    )

    if not data.get("features"):
        raise ValueError(f"Could not geocode address: {address}")

    feature = data["features"][0]
    lng, lat = feature["center"]

    return {
        "latitude": lat,
        "longitude": lng,
        "address_normalized": feature["place_name"],
    }


async def get_census_tract(lat: float, lng: float) -> str:
    """
    Returns 11-digit census tract GEOID using Census Geocoder API.
    """
    url = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params={
                "x": lng,
                "y": lat,
                "benchmark": "Public_AR_Current",
                "vintage": "Current_Current",
                "format": "json",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

    try:
        tract = data["result"]["geographies"]["Census Tracts"][0]
        state = tract["STATE"]
        county = tract["COUNTY"]
        tract_code = tract["TRACT"]
        return f"{state}{county}{tract_code}"
    except (KeyError, IndexError) as exc:
        raise ValueError(f"Could not find census tract for ({lat}, {lng})") from exc
