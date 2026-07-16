from datetime import datetime, timezone

from app.schemas.score import Factor, NeighborhoodReport, ScoreDimension, SubScore

# Stable demo lookups for local report smoke tests when Redis has no entry.
DEMO_LOOKUPS: dict[str, dict] = {
    "demo-address-001": {
        "address_raw": "123 Main St, Austin, TX 78701",
        "address_normalized": "123 Main St, Austin, TX 78701",
        "latitude": 30.2672,
        "longitude": -97.7431,
        "geoid": "48453001100",
    },
}


def _subs(*pairs: tuple[str, str, float]) -> list[SubScore]:
    return [
        SubScore(id=i, label=lab, score=sc, available=True) for i, lab, sc in pairs
    ]


def _dimension(
    score: float,
    label: str,
    summary: str,
    factors: list[Factor],
    sub_scores: list[SubScore] | None = None,
) -> ScoreDimension:
    return ScoreDimension(
        score=score,
        label=label,
        summary=summary,
        factors=factors,
        sub_scores=sub_scores or [],
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
            _subs(("access", "Access", 90), ("quality", "Quality", 88), ("timeliness", "Timeliness", 80)),
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
            _subs(("personal", "Personal crime", 76), ("property", "Property crime", 70)),
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
            _subs(("air_quality", "Air quality", 80), ("hazard", "Hazard risk", 55)),
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
            _subs(("access", "Access", 95), ("staffing", "Staffing", 86)),
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
            _subs(("income", "Income", 72), ("labor", "Labor", 62)),
        ),
        narrative=(
            "Strong hospital access and top-rated schools, with moderate flood "
            "risk to watch in spring."
        ),
        data_vintage="2024-Q4",
        computed_at=datetime.now(timezone.utc).isoformat(),
    )
