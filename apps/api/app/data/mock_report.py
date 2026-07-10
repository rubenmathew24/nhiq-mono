from datetime import datetime, timezone

from app.schemas.score import Factor, NeighborhoodReport, ScoreDimension

# Stable demo lookups for TEMP_dev_lookups.jsonl seed rows (no Redis required).
DEMO_LOOKUPS: dict[str, dict] = {
    "demo-address-001": {
        "address_raw": "123 Main St, Austin, TX 78701",
        "address_normalized": "123 Main St, Austin, TX 78701",
        "latitude": 30.2672,
        "longitude": -97.7431,
        "geoid": "48453001100",
    },
}


def _dimension(
    score: float,
    label: str,
    summary: str,
    factors: list[Factor],
) -> ScoreDimension:
    return ScoreDimension(
        score=score,
        label=label,
        summary=summary,
        factors=factors,
    )


def build_mock_report(
    *,
    address_raw: str,
    address_normalized: str,
    latitude: float,
    longitude: float,
    geoid: str,
) -> NeighborhoodReport:
    """Mock scores aligned with apps/web/src/content/landing.ts scorePreview."""
    return NeighborhoodReport(
        address=address_raw,
        address_normalized=address_normalized,
        geoid=geoid,
        latitude=latitude,
        longitude=longitude,
        overall_score=82,
        healthcare=_dimension(
            87,
            "Healthcare",
            "Strong hospital access and short ER wait times for this area.",
            [
                Factor(
                    name="Nearest hospital",
                    value="2.1 mi",
                    impact="positive",
                ),
                Factor(
                    name="ER wait time",
                    value="Below metro average",
                    impact="positive",
                ),
            ],
        ),
        safety=_dimension(
            74,
            "Safety",
            "Crime rates are moderate and trending stable year over year.",
            [
                Factor(
                    name="Violent crime index",
                    value="Near metro average",
                    impact="neutral",
                ),
                Factor(
                    name="Property crime trend",
                    value="Stable",
                    impact="positive",
                ),
            ],
        ),
        environment=_dimension(
            74,
            "Environment",
            "Air quality is generally good with moderate seasonal flood risk.",
            [
                Factor(
                    name="Air quality index",
                    value="Good",
                    impact="positive",
                ),
                Factor(
                    name="Flood risk",
                    value="Moderate",
                    impact="negative",
                ),
            ],
        ),
        education=_dimension(
            91,
            "Schools",
            "Highly rated public schools within a short commute.",
            [
                Factor(
                    name="Elementary rating",
                    value="A",
                    impact="positive",
                ),
                Factor(
                    name="High school rating",
                    value="A-",
                    impact="positive",
                ),
            ],
        ),
        economic=_dimension(
            68,
            "Economy",
            "Solid employment base with moderate home-price growth.",
            [
                Factor(
                    name="Median income trend",
                    value="Rising",
                    impact="positive",
                ),
                Factor(
                    name="Unemployment",
                    value="Slightly above metro avg",
                    impact="negative",
                ),
            ],
        ),
        narrative=(
            "Strong hospital access and top-rated schools, with moderate flood "
            "risk to watch in spring."
        ),
        data_vintage="2024-Q4",
        computed_at=datetime.now(timezone.utc).isoformat(),
    )
