from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.mock_report import DEMO_LOOKUPS, build_mock_report
from app.db.session import get_db
from app.schemas.score import NeighborhoodReport
from app.services.cache import get_lookup, get_report, save_report
from app.services.lookup_store import PostgresLookupStore
from app.services.score_service import ScoreUnavailableError, build_report_from_scores

router = APIRouter()


def _error(status: int, detail: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"detail": detail, "code": code},
    )


@router.get("/{address_id}", response_model=NeighborhoodReport)
async def get_score(
    address_id: str,
    session: AsyncSession = Depends(get_db),
):
    # Optional UI smoke-test exception — never used for fixture geocoded IDs.
    if address_id == "demo-address-001":
        lookup = DEMO_LOOKUPS["demo-address-001"]
        return build_mock_report(
            address_raw=lookup["address_raw"],
            address_normalized=lookup["address_normalized"],
            latitude=lookup["latitude"],
            longitude=lookup["longitude"],
            geoid=lookup.get("geoid") or "unknown",
        )

    cached = await get_report(address_id)
    if cached is not None:
        return NeighborhoodReport.model_validate(cached)

    lookup = await get_lookup(address_id)
    if lookup is None:
        store = PostgresLookupStore(session)
        lookup = await store.get_address_payload(address_id)
    if lookup is None:
        return _error(404, "Address lookup not found", "LOOKUP_NOT_FOUND")

    try:
        report = await build_report_from_scores(session, lookup)
    except ScoreUnavailableError:
        return _error(
            404,
            "Neighborhood score is not available for this address yet.",
            "SCORE_UNAVAILABLE",
        )

    await save_report(address_id, report.model_dump())
    return report
