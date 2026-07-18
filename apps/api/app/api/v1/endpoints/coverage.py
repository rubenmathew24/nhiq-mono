"""Public national coverage endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.coverage import CoverageResponse
from app.services.coverage_service import compute_national_coverage

router = APIRouter()


@router.get("", response_model=CoverageResponse)
async def get_coverage(session: AsyncSession = Depends(get_db)) -> CoverageResponse:
    """National data coverage overall, by source, and by state (no auth)."""
    return await compute_national_coverage(session)
