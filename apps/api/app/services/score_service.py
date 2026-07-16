"""Build live NeighborhoodReport payloads from neighborhood_scores."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.score import (
    DimensionSource,
    Factor,
    NeighborhoodReport,
    ScoreDimension,
    SubScore,
)


class ScoreUnavailableError(Exception):
    """Lookup exists but no score row for active vintage."""


def _label_for(score: float) -> str:
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Moderate"
    return "Limited"


def _parse_sub_scores(raw: Any) -> list[SubScore]:
    if not isinstance(raw, list):
        return []
    out: list[SubScore] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sid = item.get("id")
        label = item.get("label")
        if not isinstance(sid, str) or not isinstance(label, str):
            continue
        try:
            score = float(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        available = item.get("available", True)
        out.append(
            SubScore(
                id=sid,
                label=label,
                score=score,
                available=bool(available),
            )
        )
    return out


def _parse_stats_factors(raw: Any) -> list[Factor]:
    if not isinstance(raw, list):
        return []
    out: list[Factor] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        impact = item.get("impact", "neutral")
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        if impact not in ("positive", "negative", "neutral"):
            impact = "neutral"
        tone_raw = item.get("tone_score")
        tone_score: float | None = None
        if isinstance(tone_raw, (int, float)):
            tone_score = float(tone_raw)
        out.append(
            Factor(name=name, value=value, impact=impact, tone_score=tone_score)
        )
    return out


def _dimension_from_detail(
    score: float,
    label: str,
    summary: str,
    detail_block: Any,
    *,
    fallback_factors: list[Factor] | None = None,
) -> ScoreDimension:
    block = detail_block if isinstance(detail_block, dict) else {}
    sub_scores = _parse_sub_scores(block.get("sub_scores"))
    factors = _parse_stats_factors(block.get("stats"))
    if not factors and fallback_factors:
        factors = fallback_factors
    # Note limited data in summary when any sub-score unavailable
    if sub_scores and any(not s.available for s in sub_scores):
        if "limited" not in summary.lower() and "unavailable" not in summary.lower():
            summary = f"{summary} Some sub-scores use limited data."
    return ScoreDimension(
        score=float(score),
        label=label,
        summary=summary,
        factors=factors,
        sub_scores=sub_scores,
    )


def _parse_sources(raw: Any) -> dict[str, DimensionSource]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, DimensionSource] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        source_id = value.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            continue
        reason = value.get("reason")
        detail = {
            k: v
            for k, v in value.items()
            if k not in ("source_id", "reason")
        }
        out[str(key)] = DimensionSource(
            source_id=source_id,
            reason=str(reason) if reason is not None else None,
            detail=detail,
        )
    return out


def _environment_summary(score: float, sources: dict[str, DimensionSource]) -> str:
    env = sources.get("environment")
    source_id = env.source_id if env else None
    if source_id == "epa_aqs":
        return (
            f"{_label_for(score)} air quality from EPA monitor readings "
            f"for this county."
        )
    if source_id == "open_meteo":
        return (
            f"{_label_for(score)} air quality from Open-Meteo modeled US AQI "
            f"(EPA monitors unavailable or too sparse for this county)."
        )
    return f"{_label_for(score)} air-quality environment score for this area."


def _safety_summary(score: float, sources: dict[str, DimensionSource]) -> str:
    src = sources.get("safety")
    source_id = src.source_id if src else None
    if source_id == "fbi_cde":
        return (
            f"{_label_for(score)} relative safety from FBI CDE local offense "
            f"counts versus the state benchmark for this county."
        )
    if source_id == "default":
        return (
            f"{_label_for(score)} default safety score "
            f"(FBI CDE unavailable for this county)."
        )
    return "Placeholder until FBI crime ingest is available."


def _education_summary(score: float, sources: dict[str, DimensionSource]) -> str:
    src = sources.get("education")
    source_id = src.source_id if src else None
    if source_id == "nces_urban":
        return (
            f"{_label_for(score)} school access and staffing signals "
            f"from NCES locations plus Urban Institute CCD stats nearby."
        )
    if source_id == "default":
        return (
            f"{_label_for(score)} default schools score "
            f"(education sources unavailable for this tract)."
        )
    return "Placeholder until education source ingest is available."


def _economic_summary(score: float, sources: dict[str, DimensionSource]) -> str:
    src = sources.get("economic")
    source_id = src.source_id if src else None
    if source_id == "acs_bls_laus":
        return (
            f"{_label_for(score)} economic health from Census ACS income/labor "
            f"indicators blended with BLS LAUS county unemployment."
        )
    if source_id == "default":
        return (
            f"{_label_for(score)} default economy score "
            f"(ACS/LAUS unavailable for this tract)."
        )
    return "Placeholder until economic source ingest is available."


def _source_phrase(sources: dict[str, DimensionSource], key: str) -> str:
    src = sources.get(key)
    return src.source_id if src else "unknown"


def _narrative(
    *,
    healthcare: float,
    safety: float,
    environment: float,
    education: float,
    economic: float,
    overall: float,
    vintage: str,
    sources: dict[str, DimensionSource],
) -> str:
    return (
        f"Overall score {overall:.1f} ({vintage}). "
        f"Healthcare {healthcare:.1f}; "
        f"safety {safety:.1f} ({_source_phrase(sources, 'safety')}); "
        f"environment {environment:.1f} ({_source_phrase(sources, 'environment')}); "
        f"schools {education:.1f} ({_source_phrase(sources, 'education')}); "
        f"economy {economic:.1f} ({_source_phrase(sources, 'economic')})."
    )


async def fetch_score_row(
    session: AsyncSession,
    geoid: str,
    *,
    vintage: str | None = None,
) -> dict[str, Any] | None:
    active = vintage or settings.SCORE_DATA_VINTAGE
    result = await session.execute(
        text(
            """
            SELECT geoid, healthcare_score, safety_score, environment_score,
                   education_score, economic_score, overall_score,
                   data_vintage, computed_at, score_sources, score_detail
            FROM neighborhood_scores
            WHERE geoid = :geoid AND data_vintage = :vintage
            LIMIT 1
            """
        ),
        {"geoid": geoid, "vintage": active},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def build_report_from_scores(
    session: AsyncSession,
    lookup: dict[str, Any],
) -> NeighborhoodReport:
    """
    Map neighborhood_scores → NeighborhoodReport.

    Raises ScoreUnavailableError when geoid/vintage has no row.
    """
    geoid = (lookup.get("geoid") or "").strip()
    if not geoid or geoid == "unknown":
        raise ScoreUnavailableError("No census tract for this lookup")

    try:
        row = await fetch_score_row(session, geoid)
    except Exception:
        # Older DBs without score_detail column — retry without it
        result = await session.execute(
            text(
                """
                SELECT geoid, healthcare_score, safety_score, environment_score,
                       education_score, economic_score, overall_score,
                       data_vintage, computed_at, score_sources
                FROM neighborhood_scores
                WHERE geoid = :geoid AND data_vintage = :vintage
                LIMIT 1
                """
            ),
            {"geoid": geoid, "vintage": settings.SCORE_DATA_VINTAGE},
        )
        mapped = result.mappings().first()
        row = dict(mapped) if mapped else None
        if row is not None:
            row["score_detail"] = {}

    if row is None:
        raise ScoreUnavailableError(
            "Neighborhood score is not available for this address yet."
        )

    healthcare = float(row["healthcare_score"] or 0)
    safety = float(row["safety_score"] or 0)
    environment = float(row["environment_score"] or 0)
    education = float(row["education_score"] or 0)
    economic = float(row["economic_score"] or 0)
    overall = float(row["overall_score"] or 0)
    vintage = str(row["data_vintage"] or settings.SCORE_DATA_VINTAGE)
    sources = _parse_sources(row.get("score_sources"))
    detail_raw = row.get("score_detail") or {}
    if isinstance(detail_raw, str):
        import json

        try:
            detail_raw = json.loads(detail_raw)
        except json.JSONDecodeError:
            detail_raw = {}
    detail = detail_raw if isinstance(detail_raw, dict) else {}

    computed = row.get("computed_at")
    if isinstance(computed, datetime):
        computed_at = computed.astimezone(timezone.utc).isoformat()
    else:
        computed_at = datetime.now(timezone.utc).isoformat()

    return NeighborhoodReport(
        address=lookup["address_raw"],
        address_normalized=lookup["address_normalized"],
        geoid=geoid,
        latitude=float(lookup["latitude"]),
        longitude=float(lookup["longitude"]),
        overall_score=overall,
        healthcare=_dimension_from_detail(
            healthcare,
            "Healthcare",
            f"{_label_for(healthcare)} hospital access based on nearby emergency facilities.",
            detail.get("healthcare"),
        ),
        safety=_dimension_from_detail(
            safety,
            "Safety",
            _safety_summary(safety, sources),
            detail.get("safety"),
        ),
        environment=_dimension_from_detail(
            environment,
            "Environment",
            _environment_summary(environment, sources),
            detail.get("environment"),
        ),
        education=_dimension_from_detail(
            education,
            "Schools",
            _education_summary(education, sources),
            detail.get("education"),
        ),
        economic=_dimension_from_detail(
            economic,
            "Economy",
            _economic_summary(economic, sources),
            detail.get("economic"),
        ),
        narrative=_narrative(
            healthcare=healthcare,
            safety=safety,
            environment=environment,
            education=education,
            economic=economic,
            overall=overall,
            vintage=vintage,
            sources=sources,
        ),
        data_vintage=vintage,
        computed_at=computed_at,
        sources=sources,
    )
