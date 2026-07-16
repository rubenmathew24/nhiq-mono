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
- Web `ScoreBreakdown`: each category is an **interactive box** (bordered/surface control); always show category score + sub-score mini bars; expanded region lists `factors`. Do **not** rely on subtle “View details” microcopy.
- Affordance: full-box activate + `aria-expanded` / button semantics (not hover-only).
- Factor value coloring for scored stats (esp. ER wait): map via the same tiers as `scoreTier` / ScoreBar (≥75 good, ≥50 mid, else poor). Prefer deriving display color from a numeric tone (`tone_score` optional on factor **or** worker-set `impact` that matches those bands). Fix timeliness scoring so wait ≈/above national is not “good.”
- `sources` provenance unchanged; may add `fema_nri` / `cms_timely_effective_care` under environment/healthcare. User-visible Environment AQI copy omits internal source ids.

**Rationale**: Explore feedback — subtle link failed SC-002; wait green at 162 min misled users.

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

- Unit: hazard→sub-score map; timely→sub-score; property-crime blend; `score_detail` serialization; ER ordinal labels; schools-by-level; safety plain-English labels; AQI without source id; employment rate stat; wait tone vs national  
- API: report JSON includes `sub_scores` + non-empty `factors` for Bentonville after prep  
- Web Vitest: category **box** expand/collapse, affordance present without “View details”-only, factor tone classes, limited-data copy  
- Manual quickstart: smoke then metro_10

---

## 10. UX polish (post-implement explore) — 2026-07-16

### 10.1 Category boxes

**Decision**: Replace subtle “View details” with a full-width interactive category box (existing border/muted tokens). Entire header (title + score + bar) is the control; chevron ok as secondary cue.

**Rationale**: User feedback — current affordance too subtle for SC-002.

**Alternatives considered**: Larger text link only (rejected); modal sheet (rejected — keep in-place).

### 10.2 Healthcare ER labels + wait color

**Decision**:

1. Labels: `Nearest ER`, `2nd nearest ER`, `3rd nearest ER` (never “Also nearby”).
2. Timeliness → color: use ScoreBar tiers. Tighten `_timeliness_score` (and/or impact mapping) so local wait ≥ national (and similarly vs state when that is the primary bench) does not land in the “good” (≥75) band. Example acceptance: Bentonville ~162 min vs national ~161 → mid or poor, not green.
3. Prefer optional `tone_score` on expand stats (0–100) so web can call `scoreTextClass` without re-deriving wait math in the client (thin client). If schema stays `{name,value,impact}` only, map impact to the three tiers consistently with ScoreBar and fix the numeric score first.

**Rationale**: Ordinal labels are glanceable; current formula `100 - 25 * (local/bench)` yields ~75 when ratio≈1.0 (misleading green).

**Alternatives considered**: Keep impact-only green/amber/red without formula change (rejected — still wrong for Bentonville); show raw CMS measure ids (rejected — not plain English).

### 10.3 Safety plain English + condensed meta

**Decision**:

| Internal | User-facing label |
|----------|-------------------|
| personal sub-score | Crimes against people |
| property sub-score | Crimes against property |
| HOM / ROB / ASS / BUR / LAR | Homicide / Robbery / Assault / Burglary / Larceny (theft) |
| Geography note + up to 5 agency rows | One short grain note + one condensed agencies line (e.g. “Reported by: A; B; C” truncated), not a long list |

**Superseded for violent-crime ratio**: see §11.1 (per-resident vs state average). Do **not** show county absolute ÷ state absolute as “× state benchmark.”

**Rationale**: Codes and “personal crime” jargon fail FR-019; `ASS` is unprofessional.

### 10.4 Environment — hide Open-Meteo id

**Decision**: AQI expand value shows number + human category only (e.g. `57 · Moderate`). Do not append `(open_meteo)` / `(epa_aqs)` in user-visible stats. Provenance may remain in `score_sources` for operators/API consumers.

**Rationale**: User will address source honesty later; for now remove noise.

### 10.5 Schools — by level; drop PTR / locale

**Decision**:

1. Expand stats: for each level bucket present near the tract centroid, emit one row: **Nearest Pre-K / Elementary / Middle / Junior High / High** with name · miles.
2. Map Urban/NCES `school_level` (and grade fields when needed) into those buckets. If Junior High is not distinguishable from Middle in data, emit **Middle** only (do not invent a Junior High row).
3. Remove pupil–teacher ratio and locale code from expand stats.
4. Access sub-score: prefer average (or min) proximity across available level nearests rather than a single nearest-any-school when level data exists.
5. Staffing sub-score: `available: false` (limited data) until zoning-backed school assignment exists — do not show PTR as a proxy for “your school.”
6. Copy must not imply the listed schools are zoned/assigned to the address.

**Superseded distance rule**: see §11.3 (`SCHOOL_MAX_EXPAND_MILES = 25`).

**Rationale**: Students attend different schools by age; single nearest + PTR misleads without zoning.

**Alternatives considered**: Keep PTR with disclaimer (rejected); attendance-boundary ingest (out of scope / large).

### 10.6 Economy extras

**Decision**: Keep median household income + county unemployment. Add **Employment rate** = `employed / labor_force` from existing `acs_indicators` columns (already ingested via B23025), labeled plainly (e.g. “Share of labor force employed”) with a short percent. No new ACS variables in this polish **except population for safety normalization (§11.1)**.

**Rationale**: User asked for one/two more glanceable stats; employment rate is already in DB and understandable.

**Alternatives considered**: New poverty/rent ACS variables (deferred — needs ingest change); labor force headcount (less meaningful alone).

---

## 11. UX polish round 2 — 2026-07-16

### 11.1 Safety — per-resident vs state average

**Problem**: Current ratio `weighted_county_incidents / weighted_state_incidents` is roughly “share of statewide totals.” A small county always looks like `0.03×`, which users misread as “97% safer.”

**Decision**:

1. Compute **rates**:  
   `local_rate = weighted_local / county_pop`  
   `state_rate = weighted_state / state_pop`  
   `intensity_ratio = local_rate / state_rate` (equivalent to `(local/state) * (state_pop/county_pop)`).
2. Prefer expressing rates per 100k residents for provenance; scoring still maps `intensity_ratio` with the existing curve (`score ≈ 100 - 25 * ratio`, clamp) so ratio≈1 → ~75.
3. **User-facing expand copy** (Fair Housing–neutral), examples:  
   - ratio 0.72 → “Violent crime about 28% lower than the state average (per resident)”  
   - ratio 1.15 → “Violent crime about 15% higher than the state average (per resident)”  
   - ratio ≈1 → “Violent crime about the same as the state average (per resident)”  
   Avoid “safer/more dangerous neighborhood” language.
4. **Population source**: ACS 5-year **B01003_001E** (total population).  
   - County: sum tract populations for tracts in that county from `acs_indicators` after extending ACS ingest to store `total_population` (or payload), **or** store county-level ACS rows.  
   - State: ACS state-level B01003 for the fixture state(s) (one row per state, keyed `geo_level='state'` or sibling cache).  
   Worker path only (precompute); re-score after population available. If population missing → limited-data / unavailable comparison (do not fall back to absolute share).
5. Property-crime sub-score SHOULD use the same normalization pattern when comparable benches exist.

**Rationale**: Matches intended product meaning (“how this area compares to other places in the state”).

**Alternatives considered**: Honest relabel of absolute share (rejected — wrong product meaning); CDE summarized per-100k endpoint only (possible later; ACS pop is enough for smoke/metro).

### 11.2 Healthcare — missing stars as `★-`

**Decision**: Every ER expand value includes a star token: `★{n}` when rated, else **`★-`**. Keep `name · miles · ★…` order so columns align.

**Rationale**: User request for consistent row shape.

### 11.3 Schools — 25 mile expand cutoff

**Decision**: Constant `SCHOOL_MAX_EXPAND_MILES = 25` in worker constants. When nearest school for a level is farther (e.g. 457 mi Pre-K), emit **“No schools found within 25 mi”** (or omit row + single summary if all levels empty)—never list the distant facility. Access sub-score only averages distances for in-range schools; if none in range, access `available: false`.

**Rationale**: Bentonville smoke showed unusable Pre-K distance; 25 mi is still “somewhat far” (red tone) but not statewide absurdity. Aligns roughly with hospital far threshold (20 mi) with a bit more school leeway.

**Alternatives considered**: 15 mi (too tight for some rural fixtures); 50 mi (still too far for daily school travel).

### 11.4 Full-box click + stronger hover

**Decision**: Restructure `ScoreBreakdown` so the **entire category box** (including sub-scores + summary) is one `<button>` (or equivalent single control). Expanded stats panel remains inside the same toggle. Hover uses a clearly stronger highlight than current `hover:bg-muted/40` (e.g. stronger muted fill + slightly stronger border)—still within existing tokens, not a new color system.

**Rationale**: User feedback — only header felt clickable; hover too subtle.

**Alternatives considered**: Nested buttons for expand only (a11y hazard); pointer cursor alone without stronger hover (rejected).
