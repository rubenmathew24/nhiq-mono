"""Build neighborhood_scores.score_detail (sub_scores + expand stats)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ingest.fixtures.constants import (
    DEFAULT_ENVIRONMENT_SCORE,
    DEFAULT_HEALTHCARE_SCORE,
    HOSPITAL_FAR_MILES,
    HOSPITAL_NEAR_MILES,
)
from scoring.economic import income_score_from_median, unemployment_score_from_rate
from scoring.formulas import distance_score_miles, environment_from_aqi
from scoring.safety import CountyCrime, safety_from_cde

HC_ACCESS_W = 0.35
HC_QUALITY_W = 0.40
HC_TIMELY_W = 0.25
SAFETY_PERSONAL_W = 0.70
SAFETY_PROPERTY_W = 0.30
ENV_AIR_W = 0.60
ENV_HAZARD_W = 0.40
PROPERTY_OFFENSES = ("BUR", "LAR", "MVT", "ARS")

OFFENSE_LABELS = {
    "HOM": "Homicide",
    "ROB": "Robbery",
    "ASS": "Assault",
    "BUR": "Burglary",
    "LAR": "Larceny (theft)",
    "MVT": "Motor vehicle theft",
    "ARS": "Arson",
}

SCHOOL_LEVEL_META: list[tuple[str, str, str]] = [
    ("prek", "Nearest Pre-K", "prek"),
    ("elementary", "Nearest elementary", "elementary"),
    ("middle", "Nearest middle", "middle"),
    ("junior_high", "Nearest junior high", "junior_high"),
    ("high", "Nearest high", "high"),
]

HAZARD_RATING_SCORES = {
    "very low": 95.0,
    "relatively low": 80.0,
    "relatively moderate": 55.0,
    "relatively high": 30.0,
    "very high": 10.0,
}


@dataclass
class NearestFacility:
    name: str | None = None
    miles: float | None = None
    star_rating: int | None = None
    cms_provider_id: str | None = None


@dataclass
class TimelyMeasure:
    measure_id: str
    measure_name: str | None = None
    score_value: float | None = None
    state_score: float | None = None
    national_score: float | None = None


@dataclass
class FemaInputs:
    risk_score: float | None = None
    risk_rating: str | None = None
    hazards: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchoolByLevel:
    level: str  # prek | elementary | middle | junior_high | high
    name: str | None = None
    miles: float | None = None


@dataclass
class DetailInputs:
    nearest_ers: list[NearestFacility] = field(default_factory=list)
    avg_stars: float | None = None
    nearest_er_miles: float | None = None
    timely: TimelyMeasure | None = None
    crime: CountyCrime | None = None
    agencies: list[dict[str, Any]] = field(default_factory=list)
    school_name: str | None = None
    nearest_school_miles: float | None = None
    locale: str | None = None
    enrollment: int | None = None
    teachers_fte: float | None = None
    schools_by_level: list[SchoolByLevel] = field(default_factory=list)
    avg_aqi: float | None = None
    aqi_source: str | None = None
    aqi_category: str | None = None
    fema: FemaInputs | None = None
    median_hh_income: float | None = None
    unemployment_rate: float | None = None
    employed: float | None = None
    labor_force: float | None = None
    acs_year: str | None = None
    laus_period: str | None = None


def _sub(sid: str, label: str, score: float | None, *, available: bool) -> dict[str, Any]:
    return {
        "id": sid,
        "label": label,
        "score": round(float(score), 1) if score is not None and available else 0.0,
        "available": available,
    }


def _impact_from_tone(tone: float | None) -> str:
    """Match ScoreBar tiers: ≥75 good, ≥50 mid, else poor."""
    if tone is None:
        return "neutral"
    if tone >= 75:
        return "positive"
    if tone >= 50:
        return "neutral"
    return "negative"


def _stat(
    name: str,
    value: str,
    impact: str = "neutral",
    tone_score: float | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {"name": name, "value": value, "impact": impact}
    if tone_score is not None:
        row["tone_score"] = round(float(tone_score), 1)
    return row


def _blend(parts: list[tuple[float, float]]) -> float | None:
    if not parts:
        return None
    total_w = sum(w for w, _ in parts)
    if total_w <= 0:
        return None
    return sum(w * s for w, s in parts) / total_w


def _star_score(avg_stars: float | None) -> float | None:
    if avg_stars is None:
        return None
    return (float(avg_stars) - 1.0) / 4.0 * 100.0


def _timeliness_score(timely: TimelyMeasure | None) -> float | None:
    """Map ER wait minutes vs benchmark to 0–100 (higher = better).

    At parity with the primary bench → ~50 (mid tier), so waits at/above
    national average are never ScoreBar \"good\" (≥75).
    """
    if timely is None or timely.score_value is None:
        return None
    local = float(timely.score_value)
    # Prefer national when present for SC-009; else state; else absolute heuristic
    if timely.national_score is not None and float(timely.national_score) > 0:
        bench = float(timely.national_score)
    elif timely.state_score is not None and float(timely.state_score) > 0:
        bench = float(timely.state_score)
    else:
        # Absolute: 15 min → ~85, 60 min → ~50, 120+ → poor
        return max(0.0, min(100.0, 100.0 - (local - 15.0) * (50.0 / 45.0)))
    ratio = local / bench
    return max(0.0, min(100.0, 100.0 - 50.0 * ratio))


def _property_safety(crime: CountyCrime | None) -> float | None:
    if crime is None or not crime.by_offense:
        return None
    local = 0.0
    state = 0.0
    saw = False
    for slug in PROPERTY_OFFENSES:
        pair = crime.by_offense.get(slug)
        if not pair:
            continue
        incidents, bench = pair
        local += float(incidents or 0.0)
        if bench is not None:
            state += float(bench)
            saw = True
    if not saw and local == 0.0:
        return None
    if not saw:
        state = local if local > 0 else 1.0
    ratio = local / max(state, 1e-6)
    return max(0.0, min(100.0, 100.0 - 25.0 * ratio))


def _hazard_score(fema: FemaInputs | None) -> float | None:
    if fema is None:
        return None
    if fema.risk_rating:
        key = fema.risk_rating.strip().lower()
        if key in HAZARD_RATING_SCORES:
            return HAZARD_RATING_SCORES[key]
    if fema.risk_score is not None:
        return max(0.0, min(100.0, 100.0 - float(fema.risk_score)))
    return None


def _aqi_category(avg_aqi: float | None) -> str:
    if avg_aqi is None:
        return "Unknown"
    a = float(avg_aqi)
    if a <= 50:
        return "Good"
    if a <= 100:
        return "Moderate"
    if a <= 150:
        return "Unhealthy for sensitive groups"
    if a <= 200:
        return "Unhealthy"
    return "Very unhealthy"


def healthcare_category_score(
    access: float | None,
    quality: float | None,
    timely: float | None,
) -> float:
    parts: list[tuple[float, float]] = []
    if access is not None:
        parts.append((HC_ACCESS_W, access))
    if quality is not None:
        parts.append((HC_QUALITY_W, quality))
    if timely is not None:
        parts.append((HC_TIMELY_W, timely))
    blended = _blend(parts)
    return round(blended, 1) if blended is not None else DEFAULT_HEALTHCARE_SCORE


def safety_category_score(personal: float | None, property_s: float | None) -> float:
    parts: list[tuple[float, float]] = []
    if personal is not None:
        parts.append((SAFETY_PERSONAL_W, personal))
    if property_s is not None:
        parts.append((SAFETY_PROPERTY_W, property_s))
    blended = _blend(parts)
    return round(blended, 1) if blended is not None else DEFAULT_ENVIRONMENT_SCORE


def environment_category_score(air: float | None, hazard: float | None) -> float:
    parts: list[tuple[float, float]] = []
    if air is not None:
        parts.append((ENV_AIR_W, air))
    if hazard is not None:
        parts.append((ENV_HAZARD_W, hazard))
    blended = _blend(parts)
    return round(blended, 1) if blended is not None else DEFAULT_ENVIRONMENT_SCORE


def _er_ordinal_label(index: int) -> str:
    if index == 0:
        return "Nearest ER"
    if index == 1:
        return "2nd nearest ER"
    if index == 2:
        return "3rd nearest ER"
    return f"{index + 1}th nearest ER"


def _access_from_schools(inputs: DetailInputs) -> float | None:
    miles_list: list[float] = []
    for s in inputs.schools_by_level:
        if s.miles is not None:
            miles_list.append(float(s.miles))
    if not miles_list and inputs.nearest_school_miles is not None:
        miles_list.append(float(inputs.nearest_school_miles))
    if not miles_list:
        return None
    scores = [distance_score_miles(m) for m in miles_list]
    return sum(scores) / len(scores)


def build_score_detail(inputs: DetailInputs) -> dict[str, Any]:
    access = (
        distance_score_miles(float(inputs.nearest_er_miles))
        if inputs.nearest_er_miles is not None
        else None
    )
    quality = _star_score(inputs.avg_stars)
    timely_s = _timeliness_score(inputs.timely)
    hc_subs = [
        _sub("access", "Access", access, available=access is not None),
        _sub("quality", "Quality", quality, available=quality is not None),
        _sub("timeliness", "Timeliness", timely_s, available=timely_s is not None),
    ]
    hc_stats: list[dict[str, Any]] = []
    for i, er in enumerate(inputs.nearest_ers[:3]):
        label = _er_ordinal_label(i)
        bits = [er.name or "Emergency facility"]
        if er.miles is not None:
            bits.append(f"{float(er.miles):.1f} mi")
        if er.star_rating is not None:
            bits.append(f"★{er.star_rating}")
        tone = None
        if er.miles is not None:
            tone = distance_score_miles(float(er.miles))
        impact = _impact_from_tone(tone)
        if er.miles is not None and er.miles <= HOSPITAL_NEAR_MILES and tone is None:
            impact = "positive"
        elif er.miles is not None and er.miles >= HOSPITAL_FAR_MILES and tone is None:
            impact = "negative"
        hc_stats.append(_stat(label, " · ".join(bits), impact, tone_score=tone))
    if not hc_stats:
        hc_stats.append(_stat("Nearest ER", "Unavailable", "neutral"))
    if inputs.timely and inputs.timely.score_value is not None:
        wait = f"{inputs.timely.score_value:g}"
        unit = " min" if "OP_18" in (inputs.timely.measure_id or "").upper() else ""
        cmp_bits = []
        if inputs.timely.state_score is not None:
            cmp_bits.append(f"state {inputs.timely.state_score:g}")
        if inputs.timely.national_score is not None:
            cmp_bits.append(f"national {inputs.timely.national_score:g}")
        cmp = f" ({' · '.join(cmp_bits)})" if cmp_bits else ""
        hc_stats.append(
            _stat(
                "ER wait",
                f"{wait}{unit}{cmp}",
                _impact_from_tone(timely_s),
                tone_score=timely_s,
            )
        )
    else:
        hc_stats.append(_stat("ER wait", "Unavailable", "neutral"))

    personal_res = safety_from_cde(inputs.crime)
    if inputs.crime is None or not inputs.crime.by_offense:
        personal = None
    else:
        personal = personal_res.score
    property_s = _property_safety(inputs.crime)
    safety_subs = [
        _sub(
            "personal",
            "Crimes against people",
            personal,
            available=personal is not None,
        ),
        _sub(
            "property",
            "Crimes against property",
            property_s,
            available=property_s is not None,
        ),
    ]
    safety_stats: list[dict[str, Any]] = []
    if inputs.crime and inputs.crime.by_offense:
        ratio = personal_res.provenance.get("ratio")
        if ratio is not None:
            r = float(ratio)
            tone = max(0.0, min(100.0, 100.0 - 25.0 * r))
            safety_stats.append(
                _stat(
                    "Violent crime vs state",
                    f"About {r:.2f}× the state benchmark",
                    _impact_from_tone(tone),
                    tone_score=tone,
                )
            )
        for slug in ("HOM", "ROB", "ASS", "BUR", "LAR"):
            pair = inputs.crime.by_offense.get(slug)
            if not pair:
                continue
            inc, bench = pair
            label = OFFENSE_LABELS.get(slug, slug)
            val = f"{inc:g} incidents (12 mo)"
            if bench is not None:
                val += f" · state bench {bench:g}"
            safety_stats.append(_stat(label, val, "neutral"))
        agency_names: list[str] = []
        for ag in inputs.agencies[:4]:
            nm = ag.get("agency_name") or ag.get("ori")
            if nm:
                agency_names.append(str(nm))
        about = "County/agency grain — same for tracts in this county."
        if agency_names:
            about += " Reported by: " + "; ".join(agency_names)
            if len(inputs.agencies) > 4:
                about += "; …"
        safety_stats.append(_stat("About these numbers", about, "neutral"))
    else:
        safety_stats.append(_stat("Crime data", "Unavailable", "neutral"))

    access_e = _access_from_schools(inputs)
    # Staffing limited until zoning-backed assignment exists (no PTR proxy)
    edu_subs = [
        _sub("access", "Access", access_e, available=access_e is not None),
        _sub("staffing", "Staffing", None, available=False),
    ]
    edu_stats: list[dict[str, Any]] = []
    by_level = {s.level: s for s in inputs.schools_by_level if s.level}
    for level_id, label, _ in SCHOOL_LEVEL_META:
        school = by_level.get(level_id)
        if school is None:
            continue
        bits = [school.name or "Public school"]
        tone = None
        if school.miles is not None:
            bits.append(f"{float(school.miles):.1f} mi")
            tone = distance_score_miles(float(school.miles))
        edu_stats.append(
            _stat(label, " · ".join(bits), _impact_from_tone(tone), tone_score=tone)
        )
    if not edu_stats:
        if inputs.school_name or inputs.nearest_school_miles is not None:
            bits = [inputs.school_name or "Public school"]
            tone = None
            if inputs.nearest_school_miles is not None:
                bits.append(f"{float(inputs.nearest_school_miles):.1f} mi")
                tone = distance_score_miles(float(inputs.nearest_school_miles))
            edu_stats.append(
                _stat(
                    "Nearest public school",
                    " · ".join(bits),
                    _impact_from_tone(tone),
                    tone_score=tone,
                )
            )
        else:
            edu_stats.append(_stat("Nearby schools", "Unavailable", "neutral"))

    air_available = inputs.avg_aqi is not None
    air_score = environment_from_aqi(inputs.avg_aqi) if air_available else None
    hazard = _hazard_score(inputs.fema)
    env_subs = [
        _sub("air_quality", "Air quality", air_score, available=air_available),
        _sub("hazard", "Hazard risk", hazard, available=hazard is not None),
    ]
    env_stats: list[dict[str, Any]] = []
    if air_available:
        cat = inputs.aqi_category or _aqi_category(inputs.avg_aqi)
        # Plain English only — never append internal source ids (open_meteo, epa_aqs)
        env_stats.append(
            _stat(
                "Average AQI",
                f"{float(inputs.avg_aqi):.0f} · {cat}",
                _impact_from_tone(air_score),
                tone_score=air_score,
            )
        )
    else:
        env_stats.append(_stat("Average AQI", "Unavailable", "neutral"))
    if inputs.fema and (inputs.fema.risk_rating or inputs.fema.risk_score is not None):
        rating = inputs.fema.risk_rating or "Unrated"
        extra = (
            f" (score {float(inputs.fema.risk_score):.0f})"
            if inputs.fema.risk_score is not None
            else ""
        )
        env_stats.append(
            _stat(
                "Composite hazard rating",
                rating + extra,
                _impact_from_tone(hazard),
                tone_score=hazard,
            )
        )
        for slug, block in list((inputs.fema.hazards or {}).items())[:5]:
            if not isinstance(block, dict):
                continue
            riskr = next(
                (v for k, v in block.items() if str(k).endswith("_RISKR")),
                "elevated",
            )
            nice = str(slug).replace("_", " ").title()
            env_stats.append(_stat(f"Hazard · {nice}", str(riskr), "negative"))
    else:
        env_stats.append(_stat("Hazard risk", "Unavailable", "neutral"))

    income_s = income_score_from_median(inputs.median_hh_income)
    labor_s = unemployment_score_from_rate(inputs.unemployment_rate)
    econ_subs = [
        _sub("income", "Income", income_s, available=income_s is not None),
        _sub("labor", "Labor", labor_s, available=labor_s is not None),
    ]
    econ_stats: list[dict[str, Any]] = []
    if inputs.median_hh_income is not None:
        yr = f" ({inputs.acs_year})" if inputs.acs_year else ""
        econ_stats.append(
            _stat(
                "Median household income",
                f"${float(inputs.median_hh_income):,.0f}{yr}",
                _impact_from_tone(income_s),
                tone_score=income_s,
            )
        )
    else:
        econ_stats.append(_stat("Median household income", "Unavailable", "neutral"))
    if inputs.unemployment_rate is not None:
        per = f" · {inputs.laus_period}" if inputs.laus_period else ""
        econ_stats.append(
            _stat(
                "County unemployment",
                f"{float(inputs.unemployment_rate):.1f}%{per}",
                _impact_from_tone(labor_s),
                tone_score=labor_s,
            )
        )
    else:
        econ_stats.append(_stat("County unemployment", "Unavailable", "neutral"))
    if (
        inputs.employed is not None
        and inputs.labor_force is not None
        and float(inputs.labor_force) > 0
    ):
        rate = 100.0 * float(inputs.employed) / float(inputs.labor_force)
        # Rough tone: ≥95 good, ≥90 mid, else poorer
        emp_tone = max(0.0, min(100.0, (rate - 80.0) * 5.0))
        econ_stats.append(
            _stat(
                "Share of labor force employed",
                f"{rate:.1f}%",
                _impact_from_tone(emp_tone),
                tone_score=emp_tone,
            )
        )

    return {
        "healthcare": {"sub_scores": hc_subs, "stats": hc_stats},
        "safety": {"sub_scores": safety_subs, "stats": safety_stats},
        "education": {"sub_scores": edu_subs, "stats": edu_stats},
        "environment": {"sub_scores": env_subs, "stats": env_stats},
        "economic": {"sub_scores": econ_subs, "stats": econ_stats},
    }
