# Data Model: Report Sub-Scores & Category Detail

**Feature**: `004-report-subscores` | **Date**: 2026-07-16

System of record: PostgreSQL + PostGIS. Additive changes only. Geography for new rows: counties in `smoke` / `metro_10` via existing scope helpers.

---

## Existing entities (unchanged PKs)

Reuse as inputs to scoring detail:

| Entity | Role for expand/sub-scores |
|--------|----------------------------|
| `census_tracts` | Tract centroid / geoid |
| `hospitals` | Nearest ER name, stars, distance |
| `epa_aqi_readings` + Open-Meteo at score time | Air quality |
| `crime_offense_monthly` + `crime_agency_selection` | Personal + property vs state; agency list |
| `schools_nces` + `schools_urban` | Nearest school, miles, pupil–teacher |
| `acs_indicators` + `bls_laus_county` | Income, unemployment |
| `neighborhood_scores` | Category + overall numerics; `score_sources` provenance |

---

## NeighborhoodScore (extended)

| Field | Type | Rules |
|-------|------|--------|
| … existing score columns … | | Unchanged semantics |
| score_sources | JSONB | Unchanged; may add fema/timely provenance keys |
| **score_detail** | JSONB NOT NULL DEFAULT `{}` | **NEW** — per-dimension `sub_scores` + `stats` |

**Uniqueness**: still `(geoid, data_vintage)`.

### `score_detail` shape

```json
{
  "healthcare": {
    "sub_scores": [
      {"id": "access", "label": "Access", "score": 82.0, "available": true},
      {"id": "quality", "label": "Quality", "score": 90.0, "available": true},
      {"id": "timeliness", "label": "Timeliness", "score": 71.0, "available": true}
    ],
    "stats": [
      {"name": "Nearest ER", "value": "Mercy · 2.1 mi · ★4", "impact": "positive"},
      {"name": "Also nearby", "value": "Hospital B · 4.0 mi · ★3", "impact": "neutral"},
      {"name": "ER wait", "value": "28 min (below state)", "impact": "positive"}
    ]
  },
  "safety": { "sub_scores": [], "stats": [] },
  "education": { "sub_scores": [], "stats": [] },
  "environment": { "sub_scores": [], "stats": [] },
  "economic": { "sub_scores": [], "stats": [] }
}
```

- `available: false` → UI shows limited-data for that sub-score; omit from category blend weights (renormalize).
- `stats` map 1:1 to API `factors` for expand panels.
- Empty `{}` on old rows until re-score.

### Category blend weights (when components available)

See [research.md](./research.md) §3. Category numeric columns remain the weighted blend written by the score job.

---

## FemaNriTract (new)

| Field | Type | Rules |
|-------|------|--------|
| geoid | VARCHAR(11) | PK — census tract |
| state_fips / county_fips | VARCHAR | Denormalized for scope filters |
| risk_score | NUMERIC | FEMA composite percentile (higher = more risk) |
| risk_rating | VARCHAR(64) | e.g. Relatively Moderate |
| eal_score / sovi_score / resl_score | NUMERIC | Optional composites when present |
| hazards | JSONB | Map of snake_case hazard → attribute block (Moderate+ only) |
| data_vintage | VARCHAR(10) | e.g. `2026-Q3` |
| payload | JSONB | Optional raw excerpt |
| updated_at | timestamptz | |

**Scope**: Tracts in smoke/metro_10 counties only for this feature.

**Scoring**: Invert risk → `hazard` sub-score 0–100; expand stats from `risk_rating` + top hazard (e.g. inland_flooding).

---

## HospitalTimelyMeasure (new)

| Field | Type | Rules |
|-------|------|--------|
| id | UUID | PK |
| cms_provider_id | VARCHAR(10) | FK logical → `hospitals.cms_provider_id` |
| measure_id | VARCHAR(32) | e.g. `OP_18b` |
| measure_name | VARCHAR(255) | |
| score_value | NUMERIC | Nullable if footnote/suppressed |
| score_text | VARCHAR(64) | When CMS returns non-numeric |
| sample | NUMERIC | Nullable |
| footnote | TEXT | Nullable |
| state_score | NUMERIC | Nullable benchmark |
| national_score | NUMERIC | Nullable benchmark |
| start_date / end_date | DATE | Reporting window |
| data_vintage | VARCHAR(10) | |
| updated_at | timestamptz | |

**Uniqueness**: `(cms_provider_id, measure_id, data_vintage)`.

**Scope**: Hospitals already loaded for fixture states / active counties.

**Scoring**: Primary ED measure for nearest ER(s) → timeliness sub-score + wait expand stat.

---

## Relationships

```text
CensusTract 1──1 FemaNriTract (optional)
Hospital 1──* HospitalTimelyMeasure
CensusTract 1──* NeighborhoodScore
NeighborhoodScore.score_detail ← scoring reads hospitals, schools, crime, ACS, LAUS, EPA/OM, FemaNri, Timely
AddressLookup → geoid → NeighborhoodScore → API report (sub_scores + factors)
```

---

## Validation / idempotency

- FEMA upsert on `geoid`.
- Timely upsert on `(cms_provider_id, measure_id, data_vintage)`.
- Score upsert still `(geoid, data_vintage)`; always rewrite `score_detail` on successful compute.
- Missing FEMA/timely: category scores remain computable; sub-score `available: false`; stats omit or mark unavailable.

---

## Migration notes

1. Apply `infra/sql/007_report_detail.sql` (or next free number) on existing Compose volumes:

   ```sql
   ALTER TABLE neighborhood_scores
     ADD COLUMN IF NOT EXISTS score_detail JSONB NOT NULL DEFAULT '{}'::jsonb;
   -- CREATE TABLE fema_nri_tracts ...
   -- CREATE TABLE hospital_timely_measures ...
   ```

2. **Conversion cost**: additive; no drop/rename of existing raw tables. Re-run `worker-fema` → `worker-cms-timely` → `worker-scoring` for `INGEST_SCOPE=smoke` then `metro_10`.

3. Alembic still optional; follow project SQL one-shot pattern.
