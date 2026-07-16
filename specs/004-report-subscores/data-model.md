# Data Model: Report Sub-Scores & Category Detail

**Feature**: `004-report-subscores` | **Date**: 2026-07-16 (UX polish revision)

System of record: PostgreSQL + PostGIS. Additive changes only for schema. UX polish rewrites `score_detail` JSON content (re-score); no new tables for polish.

Geography for new rows: counties in `smoke` / `metro_10` via existing scope helpers.

---

## Existing entities (unchanged PKs)

Reuse as inputs to scoring detail:

| Entity | Role for expand/sub-scores |
|--------|----------------------------|
| `census_tracts` | Tract centroid / geoid |
| `hospitals` | Nearest ER name, stars, distance (top 3) |
| `epa_aqi_readings` + Open-Meteo at score time | Air quality (source id not user-visible) |
| `crime_offense_monthly` + `crime_agency_selection` | Crimes against people/property vs state; condensed agencies |
| `schools_nces` + `schools_urban` | Nearest school **per level** (school_level / grades) |
| `acs_indicators` + `bls_laus_county` | Income, unemployment, employment rate; **total_population** (ACS B01003) for safety rate normalization (tract sum → county; state-level row for state pop) |
| `fema_nri_tracts` | Hazard sub-score / stats |
| `hospital_timely_measures` | ER wait / timeliness |
| `neighborhood_scores` | Category + overall numerics; `score_sources` provenance; `score_detail` |

---

## NeighborhoodScore (extended)

| Field | Type | Rules |
|-------|------|--------|
| … existing score columns … | | Unchanged semantics |
| score_sources | JSONB | Unchanged; may include fema/timely / open_meteo provenance keys for operators |
| **score_detail** | JSONB NOT NULL DEFAULT `{}` | Per-dimension `sub_scores` + `stats` (plain-English names) |

**Uniqueness**: still `(geoid, data_vintage)`.

### `score_detail` shape (polish)

```json
{
  "healthcare": {
    "sub_scores": [
      {"id": "access", "label": "Access", "score": 82.0, "available": true},
      {"id": "quality", "label": "Quality", "score": 90.0, "available": true},
      {"id": "timeliness", "label": "Timeliness", "score": 48.0, "available": true}
    ],
    "stats": [
      {"name": "Nearest ER", "value": "Mercy · 2.1 mi · ★4", "impact": "positive", "tone_score": 82},
      {"name": "2nd nearest ER", "value": "Hospital B · 4.0 mi · ★-", "impact": "neutral", "tone_score": 55},
      {"name": "3rd nearest ER", "value": "Hospital C · 6.2 mi · ★3", "impact": "neutral", "tone_score": 40},
      {"name": "ER wait", "value": "162 min (state 120 · national 161)", "impact": "negative", "tone_score": 48}
    ]
  },
  "safety": {
    "sub_scores": [
      {"id": "personal", "label": "Crimes against people", "score": 70.0, "available": true},
      {"id": "property", "label": "Crimes against property", "score": 65.0, "available": true}
    ],
    "stats": [
      {"name": "Violent crime vs state", "value": "About 28% lower than the state average (per resident)", "impact": "positive", "tone_score": 82},
      {"name": "Homicide", "value": "…", "impact": "neutral"},
      {"name": "About these numbers", "value": "County/agency grain — same for tracts in this county. Reported by: Agency A; Agency B", "impact": "neutral"}
    ]
  },
  "education": {
    "sub_scores": [
      {"id": "access", "label": "Access", "score": 75.0, "available": true},
      {"id": "staffing", "label": "Staffing", "score": 0.0, "available": false}
    ],
    "stats": [
      {"name": "Nearest elementary", "value": "Example Elem · 0.8 mi", "impact": "positive"},
      {"name": "Nearest Pre-K", "value": "No schools found within 30 mi", "impact": "neutral"}
    ]
  },
  "environment": {
    "sub_scores": [],
    "stats": [
      {"name": "Average AQI", "value": "57 · Moderate", "impact": "neutral", "tone_score": 60}
    ]
  },
  "economic": {
    "sub_scores": [],
    "stats": [
      {"name": "Median household income", "value": "$92,000 (2022)", "impact": "positive"},
      {"name": "County unemployment", "value": "3.1%", "impact": "positive"},
      {"name": "Share of labor force employed", "value": "96.2%", "impact": "positive"}
    ]
  }
}
```

### Field rules

- `available: false` → UI shows limited-data for that sub-score; omit from category blend weights (renormalize) when writing category score.
- `stats` map 1:1 to API `factors` for expand panels. **`name` MUST be plain English** (no `HOM`/`ASS`, no `open_meteo`, no “Also nearby”).
- Optional **`tone_score`** (0–100): web colors the value with ScoreBar tiers (`≥75` / `≥50` / else). Required for ER wait acceptance (SC-009).
- Empty `{}` on old rows until re-score.
- Schools stats: one row per available level bucket **within 30 miles**; beyond cutoff → no-schools-found copy; never include pupil–teacher or locale.
- Safety property sub-score: `available: false` when property offenses lack state benchmarks (do not emit score `0` from synthetic ratios).
- Safety violent-crime factor: per-resident vs state average plain English; never absolute county/state count share.
- Healthcare ER values: always include `★n` or `★-`.
- Safety: prefer a single condensed “About these numbers” (or equivalent) over separate geography + many agency rows.

### Category blend weights (when components available)

See [research.md](./research.md) §3 and §11.1. Personal safety ratio uses population-normalized intensity.

### ACS population (round 2)

| Field | Rules |
|-------|--------|
| `acs_indicators.total_population` (or payload key) | ACS B01003_001E at tract; county pop = sum of tracts in county |
| State population | ACS state geo_level row (or equivalent) for intensity denominator |

---

## FemaNriTract / HospitalTimelyMeasure

Unchanged from first plan — see prior sections in git history / first implement. Polish does not alter their schemas.

---

## Relationships

```text
CensusTract 1──1 FemaNriTract (optional)
Hospital 1──* HospitalTimelyMeasure
CensusTract 1──* NeighborhoodScore
NeighborhoodScore.score_detail ← scoring reads hospitals, schools (by level, ≤30 mi),
  crime + ACS population, ACS labor, LAUS, EPA/OM, FemaNri, Timely
```

---

## Validation notes

- Re-score after polish is required for fixture acceptance (labels/tone live in JSON).
- Junior High row only when data distinguishes it from Middle; otherwise Middle covers that band.
- After ACS population lands, force re-score before accepting SC-010.
