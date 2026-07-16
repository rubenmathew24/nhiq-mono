# Research: Report Sub-Scores & Category Detail

**Feature**: `004-report-subscores` | **Date**: 2026-07-16

Resolves design decisions for expanding the local/dev report with category sub-scores and expandable stats. Scope locked to **`INGEST_SCOPE=smoke`** and **`metro_10`** only (not national).

Probe ground truth: `nhiq/backend/scripts/DATA_SOURCE_OUTPUT_GUIDE.md`, `source_field_notes.json`, `data_probe/{healthcare,environment}.py`.

---

## 1. Geography / execution scope

**Decision**: Implement and verify **only** for local Docker Compose with `INGEST_SCOPE` ∈ {`smoke`, `metro_10`}. New workers MUST call `active_county_fips()` / existing fixture allowlists. Refuse or no-op national batches for FEMA/timely workers in this feature (document: “use 003 for national later”).

**Rationale**: User direction; metro_10 already has tracts/hospitals/schools/crime/ACS; smoke is Bentonville pin. National NRI + Timely ingest is a separate scale problem.

**Alternatives considered**: National-from-day-one (rejected); UI-only without new workers (rejected — FR-013/014 require hazard + timely care).

---

## 2. Where sub-scores and expand stats live

**Decision**:

1. Add additive column `neighborhood_scores.score_detail JSONB NOT NULL DEFAULT '{}'` (sibling to `score_sources`).
2. Shape (per dimension key):

```json
{
  "healthcare": {
    "sub_scores": [
      {"id": "access", "label": "Access", "score": 82.0},
      {"id": "quality", "label": "Quality", "score": 90.0},
      {"id": "timeliness", "label": "Timeliness", "score": 71.0, "available": true}
    ],
    "stats": [
      {"name": "Nearest ER", "value": "Mercy Hospital NW · 2.1 mi · ★4", "impact": "positive"},
      {"name": "ER wait (OP-18b)", "value": "28 min · below state avg", "impact": "positive"}
    ]
  }
}
```

3. Scoring worker **writes** `score_detail` when computing/updating scores for active counties.
4. API `build_report_from_scores` maps `score_detail` → `ScoreDimension.sub_scores` + `factors` (factors = expand stats). Do **not** re-query hospitals/schools on every report request for the happy path (constitution III). Optional: if `score_detail` empty on old rows, API MAY derive a thin fallback once and log — but acceptance requires re-score after migration.

**Rationale**: Precomputed; one read on report; additive migration (ALTER ADD COLUMN); no breaking change to numeric score columns.

**Alternatives considered**: Live PostGIS joins in API on expand (rejected — fat request path, violates precompute); only enrich `score_sources` (rejected — provenance ≠ UI stats); separate `neighborhood_score_details` table (ok but extra join; JSONB on same row is enough for metro scale).

---

## 3. Sub-score formulas (category composition)

Preserve published overall weights. Within each category:

| Category | Sub-scores | Weights when all available | Missing-component rule |
|----------|------------|------------------------------|-------------------------|
| Healthcare | access, quality, timeliness | 0.35 / 0.40 / 0.25 | Drop missing; renormalize remaining (today’s stars+distance if no timely) |
| Safety | personal, property | 0.70 / 0.30 | Personal-only if property offenses missing (current behavior ≈ personal) |
| Education | access, staffing | 0.55 / 0.45 | Same as existing education blend |
| Environment | air_quality, hazard | 0.60 / 0.40 | Air-only if no NRI row (current AQI path) |
| Economic | income, labor | 0.60 / 0.40 | Same as existing economic blend |

**Access (healthcare)**: reuse `distance_score_miles(nearest_er_miles)`.  
**Quality**: reuse star map from nearest-3 ER avg.  
**Timeliness**: map primary ED wait measure (prefer OP-18b or documented ED median minutes) vs state benchmark → 0–100 (at/below state → high).  
**Personal / property (safety)**: personal = current HOM/ROB/ASS ratio map; property = BUR/LAR/MVT(/ARS) vs state with same curve.  
**Hazard**: invert FEMA composite risk band/score to NeighborhoodIQ “higher = better” (e.g. Very High risk → low sub-score). Prefer `RISK_RATNG` band map + optional `RISK_SCORE` percentile.

**Rationale**: Matches research package; keeps backward-compatible scores when new tables empty.

---

## 4. FEMA NRI worker

**Decision**: New `workers/ingest/fema/` (Compose `worker-fema`) loading tract NRI for `active_county_fips()` only.

- Source: ArcGIS National Risk Index census-tract FeatureServer (probe-verified Bentonville).
- Persist: `fema_nri_tracts` with geoid PK, composite risk fields, `hazards` JSONB (Moderate+ only, probe inclusion rule), `data_vintage`, `updated_at`.
- Checkpoint: skip geoids already present unless force.
- Join scoring on `census_tracts.geoid`.

**Rationale**: Spec FR-013; probe already nested hazards; OpenFEMA bulk optional later for national.

**Alternatives considered**: County-only NRI (rejected — report is tract-grained); skip FEMA and fake flood from AQI (rejected).

---

## 5. CMS Timely & Effective Care worker

**Decision**: New `workers/ingest/cms_timely/` (or `cms_timely` module under ingest) Compose `worker-cms-timely`.

- Pull hospital-level Timely & Effective Care measures for facilities already in `hospitals` for fixture states (or state allowlist from active counties).
- Prefer ED-focused measure set documented in code (e.g. OP-18 variants, EDV) with state + national benchmark columns when present.
- Persist: `hospital_timely_measures` keyed by `(cms_provider_id, measure_id, data_vintage)`.
- Scoring: for nearest ER(s), pick primary measure → timeliness sub-score + expand stats.

**Rationale**: Spec FR-014; probe already ranks county/ZIP and joins benchmarks. Grain is facility — correct for “nearest ER wait.”

**Caveat (probe)**: Some timely datasets are state/national aggregates; worker MUST prefer hospital-level rows and treat missing hospital measures as unavailable (not invent from state-only).

**Alternatives considered**: Only show state median without hospital link (rejected — weak UX); HCAHPS in same worker (deferred).

---

## 6. API / web contract

**Decision**:

- Extend `ScoreDimension` with `sub_scores: list[SubScore]` (`id`, `label`, `score`, optional `available`).
- Keep `factors` as the expand-stat list (name/value/impact) populated from `score_detail.*.stats`.
- Web `ScoreBreakdown`: accordion rows; always show category score + sub-score mini bars; chevron / “View details”; expanded region lists `factors`.
- Affordance: visible control + `aria-expanded` / button semantics (not hover-only).
- `sources` provenance unchanged; may add `fema_nri` / `cms_timely_effective_care` under environment/healthcare.

**Rationale**: Minimal schema churn for web types; factors already in mock report.

---

## 7. Migration / conversion cost (confirmed)

| Change | Cost for existing Compose volumes |
|--------|-----------------------------------|
| `ALTER … ADD score_detail JSONB` | Seconds; null-safe default `{}` |
| Create `fema_nri_tracts`, `hospital_timely_measures` | Seconds |
| Re-score metro_10 / smoke | Minutes–tens of minutes depending on tract count |
| Full FEMA + Timely ingest for metro_10 | Operator session; network to ArcGIS + CMS |

No destructive rewrite of hospitals/schools/crime/ACS tables.

---

## 8. Out of scope (reaffirmed)

- `INGEST_SCOPE=national` for new workers  
- NPPES pharmacies/urgent care  
- Zillow/Redfin  
- HCAHPS / full Hospital Compare catalog  
- Azure Job scheduling for FEMA/Timely (local Compose profiles only)  
- Changing overall dimension weights (25/25/20/15/15)

---

## 9. Testing strategy

- Unit: hazard→sub-score map; timely→sub-score; property-crime blend; `score_detail` serialization  
- API: report JSON includes `sub_scores` + non-empty `factors` for Bentonville after prep  
- Web Vitest: accordion expand/collapse, affordance present, limited-data copy  
- Manual quickstart: smoke then metro_10
