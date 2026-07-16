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
                    name="Nearest ER",
                    value="Demo Hospital · 2.1 mi · ★4",
                    impact="positive",
                    tone_score=90,
                ),
                Factor(
                    name="ER wait",
                    value="22 min (state 35 · national 30)",
                    impact="positive",
                    tone_score=80,
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
                    name="Violent crime vs state",
                    value="About 1.0× the state benchmark",
                    impact="neutral",
                    tone_score=60,
                ),
                Factor(
                    name="Assault",
                    value="Near average for the area",
                    impact="neutral",
                ),
            ],
            _subs(
                ("personal", "Crimes against people", 76),
                ("property", "Crimes against property", 70),
            ),
        ),
        environment=_dimension(
            74,
            "Environment",
            "Air quality is generally good with moderate seasonal flood risk.",
            [
                Factor(
                    name="Average AQI",
                    value="42 · Good",
                    impact="positive",
                    tone_score=80,
                ),
                Factor(
                    name="Flood risk",
                    value="Moderate",
                    impact="negative",
                    tone_score=45,
                ),
            ],
            _subs(("air_quality", "Air quality", 80), ("hazard", "Hazard risk", 55)),
        ),
        education=_dimension(
            91,
            "Schools",
            "Public schools nearby across grade levels.",
            [
                Factor(
                    name="Nearest elementary",
                    value="Demo Elem · 0.8 mi",
                    impact="positive",
                    tone_score=90,
                ),
                Factor(
                    name="Nearest high",
                    value="Demo High · 2.0 mi",
                    impact="positive",
                    tone_score=85,
                ),
            ],
            [
                SubScore(id="access", label="Access", score=95, available=True),
                SubScore(id="staffing", label="Staffing", score=0.0, available=False),
            ],
        ),
        economic=_dimension(
            68,
            "Economy",
            "Solid employment base with moderate home-price growth.",
            [
                Factor(
                    name="Median household income",
                    value="$85,000",
                    impact="positive",
                    tone_score=72,
                ),
                Factor(
                    name="County unemployment",
                    value="4.2%",
                    impact="neutral",
                    tone_score=55,
                ),
                Factor(
                    name="Share of labor force employed",
                    value="95.1%",
                    impact="positive",
                    tone_score=80,
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
