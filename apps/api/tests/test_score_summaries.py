"""Live score copy tracks score_sources (no stale placeholder narratives)."""

from app.schemas.score import DimensionSource
from app.services.score_service import (
    _economic_summary,
    _education_summary,
    _narrative,
    _safety_summary,
)


def _src(source_id: str) -> DimensionSource:
    return DimensionSource(source_id=source_id)


def test_safety_summary_uses_fbi_when_sourced():
    text = _safety_summary(99.2, {"safety": _src("fbi_cde")})
    assert "Placeholder" not in text
    assert "FBI CDE" in text


def test_education_and_economic_summaries_when_sourced():
    edu = _education_summary(90.0, {"education": _src("nces_urban")})
    econ = _economic_summary(80.0, {"economic": _src("acs_bls_laus")})
    assert "Placeholder" not in edu
    assert "Placeholder" not in econ
    assert "NCES" in edu
    assert "staffing signals" not in edu.lower()
    assert "Urban Institute CCD" not in edu
    assert "by level" in edu
    assert "ACS" in econ


def test_narrative_lists_live_sources_not_interim_placeholders():
    sources = {
        "safety": _src("fbi_cde"),
        "environment": _src("open_meteo"),
        "education": _src("nces_urban"),
        "economic": _src("acs_bls_laus"),
    }
    text = _narrative(
        healthcare=88.0,
        safety=99.2,
        environment=81.0,
        education=95.0,
        economic=81.0,
        overall=90.4,
        vintage="2026-Q3",
        sources=sources,
    )
    assert "interim placeholders" not in text.lower()
    assert "fbi_cde" in text
    assert "nces_urban" in text
    assert "acs_bls_laus" in text
