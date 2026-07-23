"""Public Discover tracts-in-bbox endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.discover import DiscoverTractsResponse
from app.services.discover_service import (
    DiscoverBBoxError,
    fetch_tracts_in_bbox,
)

router = APIRouter()


def _error(status_code: int, detail: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "code": code},
    )


@router.get("/tracts", response_model=DiscoverTractsResponse)
async def get_discover_tracts(
    min_lng: float = Query(...),
    min_lat: float = Query(...),
    max_lng: float = Query(...),
    max_lat: float = Query(...),
    place_name: str | None = Query(None, max_length=200),
    session: AsyncSession = Depends(get_db),
):
    """Return bbox tracts + city-scoped summary with overall scores (public POC)."""
    try:
        return await fetch_tracts_in_bbox(
            session,
            min_lng=min_lng,
            min_lat=min_lat,
            max_lng=max_lng,
            max_lat=max_lat,
            place_name=place_name,
        )
    except DiscoverBBoxError as exc:
        return _error(status.HTTP_400_BAD_REQUEST, exc.detail, exc.code)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong. Please try again.",
        ) from None
