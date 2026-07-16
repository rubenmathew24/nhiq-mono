"""Build live NeighborhoodReport payloads from neighborhood_scores."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.score import DimensionSource, Factor, NeighborhoodReport, ScoreDimension


class ScoreUnavailableError(Exception):
    """Lookup exists but no score row for active vintage."""


def _label_for(score: float) -> str:
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Moderate"
    return "Limited"


def _dimension(
    score: float,
    label: str,
    summary: str,
    factors: list[Factor] | None = None,
) -> ScoreDimension:
    return ScoreDimension(
        score=float(score),
        label=label,
        summary=summary,
        factors=factors or [],
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
                   data_vintage, computed_at, score_sources
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

    row = await fetch_score_row(session, geoid)
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
    computed = row.get("computed_at")
    if isinstance(computed, datetime):
        computed_at = computed.astimezone(timezone.utc).isoformat()
    else:
        computed_at = datetime.now(timezone.utc).isoformat()

    env_src = sources.get("environment")
    env_factors = [
        Factor(
            name="Environment score",
            value=f"{environment:.1f}",
            impact="positive" if environment >= 60 else "neutral",
        )
    ]
    if env_src:
        env_factors.append(
            Factor(
                name="Data source",
                value=env_src.source_id,
                impact="neutral",
            )
        )

    return NeighborhoodReport(
        address=lookup["address_raw"],
        address_normalized=lookup["address_normalized"],
        geoid=geoid,
        latitude=float(lookup["latitude"]),
        longitude=float(lookup["longitude"]),
        overall_score=overall,
        healthcare=_dimension(
            healthcare,
            "Healthcare",
            f"{_label_for(healthcare)} hospital access based on nearby emergency facilities.",
            [
                Factor(
                    name="Healthcare score",
                    value=f"{healthcare:.1f}",
                    impact="positive" if healthcare >= 60 else "neutral",
                )
            ],
        ),
        safety=_dimension(
            safety,
            "Safety",
            _safety_summary(safety, sources),
            [
                Factor(
                    name="Safety score",
                    value=f"{safety:.1f}",
                    impact="positive" if safety >= 60 else "neutral",
                )
            ],
        ),
        environment=_dimension(
            environment,
            "Environment",
            _environment_summary(environment, sources),
            env_factors,
        ),
        education=_dimension(
            education,
            "Schools",
            _education_summary(education, sources),
            [
                Factor(
                    name="Education score",
                    value=f"{education:.1f}",
                    impact="positive" if education >= 60 else "neutral",
                )
            ],
        ),
        economic=_dimension(
            economic,
            "Economy",
            _economic_summary(economic, sources),
            [
                Factor(
                    name="Economic score",
                    value=f"{economic:.1f}",
                    impact="positive" if economic >= 60 else "neutral",
                )
            ],
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
