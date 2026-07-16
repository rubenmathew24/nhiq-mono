# Research: Data Ingestion Workers

**Feature**: `002-data-ingestion-workers` | **Date**: 2026-07-14 (reopened: safety / education / economic)

Resolves technical decisions for local Docker, fixture-county-scoped ingestion/scoring, live score reports, and **phased reopen** of safety → education → economic sources.

**Primary external research**: sibling repo probe suite  
`/Users/rubenmathew/Documents/My Projects/NHIQ/nhiq/backend/scripts/`  
(`DATA_SOURCE_OUTPUT_GUIDE.md`, `source_field_notes.json`, `data_probe/*`).  
Also: `docs/nhiq-design-main/07-data-ingestion-workers.md`, `08-database-schema.md`, constitution, clarified [spec.md](./spec.md), and as-built workers on this branch.

---

## 0. Source map (probe → NeighborhoodIQ pillars)

Probe `source_id` values grouped by product pillar. **002 status** = role in *this* feature.

| Pillar | Probe `source_id`(s) | Grain | 002 status |
|--------|----------------------|-------|------------|
| Geography | `census_geocoder_bootstrap`, `census_tiger_line` | point / block | API Mapbox + Census / FCC-style QA; **TIGER tracts** ingested for fixture counties |
| Healthcare quality | `cms_hospital_general_info`, `cms_hospital_compare`, `cms_hcahps`, `cms_timely_effective_care` | facility / catalog | **Hospital General Info** ingested (stars + ER); Timely/HCAHPS remain discovery/benchmark later |
| Healthcare identity | `cms_nppes_npi` | ZIP+city+state, NPI-2 orgs | **Not ingested in 002**; preferred coords enrichment for next healthcare slice |
| Environment AQ | `open_meteo_climate_data` (modeled), EPA AQS (design/AQS worker) | lat/lon vs county monitors | **EPA AQS worker** satisfies FR-002; Open-Meteo recommended upgrade |
| Environment hazards / equity | `fema_nri`, `epa_ejscreen` | tract / block-group | Out of 002 (FR-013 FEMA); NRI **verified** Bentonville in probe |
| Safety | `fbi_crime_data_explorer` | agency aggregate (≤5 ORIs) | **R1 in scope** — CDE chart worker replaces skeleton |
| Education | `nces_school_data`, `urban_school_data` | school points / directory | **R2 in scope** — both sources required (complementary fields) |
| Demographics / economic | `census_acs`, `bls_laus`, `census_bfs`, `hud_fmr`, `zillow_research`, `redfin_data_center` | ZCTA/tract/county | **R3 in scope** — ACS + BLS LAUS only; Zillow/Redfin still out (FR-013) |
| Amenities / mobility | `osm_pois`, `usda_food_access_atlas`, `epa_smart_location_db`, `dot_hpms_aadt` | point / tract / segment | Deferred |

**Decision**: Treat the probe guide as the **canonical catalog** of how each upstream behaves (auth, grain, stable keys, production path). Workers in this monorepo implement a **fixture-county ETL subset** for 002, not the entire probe fleet.

---

## 1. Execution environment

**Decision**: Local Docker Compose only (`db` + Redis + `api` + `web` + one-off `worker-*` profile services). No Azure Container Apps Jobs, no CI deploy to Azure, no work targeting `master` for this feature.

**Rationale**: Spec FR-012 / user direction — prove workers + reports locally first.

**Alternatives considered**: Azure Jobs now (rejected — out of scope); host-venv-only workers without Compose DB (rejected — PostGIS + parity with product path matter).

---

## 2. Language / runtime for workers

**Decision**: Python 3.12 under `workers/`, same major as FastAPI (`docker/worker.Dockerfile` already `python:3.12-slim`).

**Rationale**: Design doc workers are Python; probe harness is Python; future Claude narratives share the ecosystem with `apps/api`.

**Alternatives considered**: Copy entire probe package into monorepo (rejected for 002 — keep ETL workers thin; reuse patterns/env names instead).

---

## 3. Fixture geography model

**Decision**: Checked-in fixture module lists the 10 addresses and fixture county FIPS allowlist. All ingest filters and scoring iterate that allowlist (not 50 states).

| # | Address | County FIPS |
|---|---------|-------------|
| 1 | 609 SE Jamaica Dr, Bentonville, AR 72712 | `05007` |
| 2 | 233 S Wacker Dr, Chicago, IL 60606 | `17031` |
| 3 | 350 5th Ave, New York, NY 10118 | `36061` |
| 4 | 98 San Jacinto Blvd, Austin, TX 78701 | `48453` |
| 5 | 400 Broad St, Seattle, WA 98109 | `53033` |
| 6 | 1001 Brickell Bay Dr, Miami, FL 33131 | `12086` |
| 7 | 1700 Broadway, Denver, CO 80202 | `08031` |
| 8 | 191 Peachtree St NE, Atlanta, GA 30303 | `13121` |
| 9 | 1 Market St, San Francisco, CA 94105 | `06075` |
| 10 | 2 N Central Ave, Phoenix, AZ 85004 | `04013` |

**Rationale**: Spec requires county-scoped scores; probe bootstrap showed Bentonville (`AR_test`) is the validation pin for FEMA/FBI explorations.

**Probe alignment**: `census_geocoder_bootstrap` fills lat/lon + FIPS + `county_name` (latter critical for FBI ORI jurisdiction). Production online path may use Mapbox + local PostGIS PIP; probe uses Census oneline/coordinates.

---

## 4. EPA AQS ingest + Open-Meteo environment fallback

### 4a. EPA ingest (FR-002 — unchanged)

**Decision**: Call EPA AQS `dailyData` by **state** for fixture states, filter to fixture county FIPS, upsert `epa_aqi_readings`. Use lag/lookback window (`EPA_END_LAG_DAYS` / `EPA_LOOKBACK_DAYS`) because “yesterday” is often empty. Parameters: Ozone / PM2.5 / SO2. Auth: `EPA_AQS_EMAIL` + `EPA_AQS_KEY`. Deduplicate before upsert when AQS returns multiple site/standard rows for the same county-day-parameter.

**Observed**: Local fixture run produced AQI in only ~5/10 counties; Benton County often **empty**.

### 4b. Scoring policy (clarified 2026-07-14)

**Decision**:

1. **Primary**: County EPA average AQI over the scoring window when **worthy** — at least `EPA_MIN_DISTINCT_DAYS` (default **7**) distinct `date_local` values with non-null AQI.
2. **Fallback**: If EPA missing or sparse, call **Open-Meteo** Air Quality API (`us_aqi`, `cams_global`) at the **county tract-collection centroid**, mean of daily-max AQI over `OPEN_METEO_LOOKBACK_DAYS` (30). Apply the same `environment_from_aqi` curve.
3. **Last resort**: Documented default environment score **50.0** if both fail.
4. **Provenance**: Persist under `neighborhood_scores.score_sources.environment` with `source_id` ∈ {`epa_aqs`, `open_meteo`, `default`}, plus `reason` (`primary` | `fallback_no_epa` | `fallback_sparse_epa` | `both_unavailable`) and metrics (`avg_aqi`, `distinct_days`, …). API returns `sources` for a future showcase UI (UI out of scope now).

**Rationale**: Keeps regulatory/monitor data when available; avoids blank Bentonville-class counties; Open-Meteo probe path is production-proven in sibling research.

**Licensing / interpretation**: Open-Meteo air quality is **modeled** (CAMS), not EPA regulatory monitors. Commercial redistribution may require an [Open-Meteo license](https://open-meteo.com/en/pricing). Richer climate/seasonal packaging beyond the scoring fallback remains a later enhancement.

**Alternatives considered**: Open-Meteo-only (rejected — user wants EPA primary); silent default 50 (rejected — now reserved for dual failure).

---

## 5. Census tract ingest strategy

**Decision**: Download TIGER/Line tract zip **per fixture state**, GeoPandas → EPSG:4326, filter to fixture `STATEFP`+`COUNTYFP`, upsert `census_tracts` on `geoid`.

**Probe alignment**: `census_tiger_line` (FCC block) is **QA/redundancy** only; production polygons still require hosted TIGER (this worker). Bootstrap geocoder is infrastructure for address workflows, not a substitute for PostGIS polygons.

**Rationale**: Matches FR-004 / FR-018.

---

## 6. CMS hospital ingest strategy (revised)

### 6a. Probe facts

- `cms_hospital_general_info` catalog search is **discovery**; the Provider Data Catalog **Hospital General Information** dataset (`xubh-q36u`) returns facility metadata (CCN/`facility_id`, stars, ER flag, address) **without lat/lng**.
- `cms_nppes_npi` is the **primary facility enumeration** layer (NPI-2 orgs, NUCC taxonomies, LOCATION address) — best identity graph; rate-limited live API → production should prefer the **monthly NPPES dump**.
- `cms_timely_effective_care` is a **reference/benchmark** layer (ED measures, state/national)—not a neighborhood-grain score input by itself.
- Stars / Compare / HCAHPS unify later on CMS facility id / CCN.

### 6b. 002 implementation decision

**Decision**:

1. Page CMS datastore `…/query/xubh-q36u/0` (Hospital General Information).
2. Filter to **fixture state abbreviations**.
3. Map field aliases (`citytown`, `telephone_number`, `countyparish`, `hospital_overall_rating`, `emergency_services`).
4. Because lat/lng are absent: geocode **unique ZIPs** (Zippopotam.us) → set `latitude`/`longitude`/`geometry` (ZIP centroid; good enough for ≤2 mi / ≥20 mi distance bands at county scale).
5. Upsert on `cms_provider_id`; null invalid star ratings (“Not Available”).

**Rationale**: Satisfies FR-005 / SC-003 with real CMS stars + spatial nearest-ER scoring without inventing hospital locations.

**Next-slice recommendation**: Join / geocode via **NPPES LOCATION** (or street Census geocoder) for hospital-precise distance; keep CMS for quality stars/ER.

**Alternatives considered**: Hard-code hospitals (rejected); require native CMS coords (impossible on current dataset); ingest national hospitals with no filter (allowed technically, messaged as fixture-scoped via state filter).

---

## 7. Scoring algorithm (local)

**Decision**: `workers/scoring/compute.py` + pure helpers. Placeholders apply **only** for dimensions not yet delivered in the current reopen phase.

| Dimension | Weight | Status |
|-----------|--------|--------|
| healthcare | 0.25 | **Done** — nearest-3 ER star avg (60%) + distance decay ≤2 mi → 100, ≥20 mi → 0 (40%); default **50.0** if none |
| safety | 0.25 | **R1** — FBI CDE (§8); until R1 ships use placeholder **65.0** |
| education | 0.20 | **R2** — NCES + Urban (§16); until R2 ships use placeholder **70.0** |
| environment | 0.15 | **Done** — EPA → Open-Meteo → **50.0**; `max(0, 100 - avg_aqi/3)` |
| economic | 0.15 | **R3** — ACS + BLS LAUS (§17); until R3 ships use placeholder **60.0** |

Score **every** fixture-county tract. Upsert `(geoid, data_vintage)`. Active vintage: **`2026-Q3`**.

**Provenance**: Each dimension that leaves placeholders MUST write `score_sources.{dimension}` with stable `source_id`(s) and reasons (same pattern as environment/healthcare).

---

## 8. Safety phase (R1) — FBI CDE chart ingest

### 8a. Decision (in scope for 002 reopen)

**Decision**: Upgrade `workers/ingest/fbi/run.py` from skeleton to a real **fixture-county CDE chart** loader. Env: **`FBI_CDE_API_KEY`** (required for R1). Optional knobs from probe: `FBI_CDE_MAX_AGENCY_DISTANCE_MILES`, `FBI_CDE_CHART_OFFENSES` (HOM required if set), `FBI_CDE_CHART_DETAIL=default|detailed`.

### 8b. Extract path (probe-verified)

1. For each fixture address/county, resolve lat/lon + state abbr + `county_name` (from fixture metadata or census bootstrap pattern).
2. `…/agency/byStateAbbr/{ST}` → nearest filter → up to **5** ORIs (default 15 mi, widen ×1.5 once; denylist campus/park/airport; jurisdiction checks).
3. Per offense slug (default `HOM,ROB,ASS,BUR,LAR,MVT,ARS`) fetch agency + state summarized charts.
4. Merge monthly series → **agency_aggregate** grain (not tract rates). Persist ORI selection + offense/benchmark payloads (see data-model).
5. **HOM must succeed** for a county selection or fail that county unit loudly; sparse other offenses may omit with limitations logged.
6. Fair Housing / steering: present neutrally; zeros ≠ “safe.”

### 8c. Safety score formula (tract)

**Decision**:

1. Attach each fixture-county tract to that county’s selected ORI aggregate (same safety input for all tracts in the county—honest to agency grain).
2. Build a **violent/property severity index** from last-12-month offense levels vs state `benchmark_12mo` (prefer ROB+ASS+HOM for “personal safety” weighting; include property offenses at lower weight). Document exact weights in `formulas` when implementing.
3. Map relative rates to 0–100: at/below state benchmark → high score (near 85–100); substantially above → lower (toward 0–40). Clamp.
4. If CDE unavailable for a county after retries: use documented default **50.0** with `score_sources.safety.source_id=default` (not silent placeholder 65) **or** fail the phase for that fixture county—prefer **default + provenance** so other counties still ship (matches environment dual-failure pattern).
5. Provenance example: `{ "source_id": "fbi_cde", "reason": "agency_aggregate", "ori_count": 3, "primary_ori": "…" }`.

**Rationale**: Spec FR-008/008a; probe CDE path verified for Bentonville-class geographies.

**Alternatives considered**: Leave skeleton (rejected — reopen clarification); invent tract-level UCR without source (rejected).

---

## 9. Live report API path

**Decision**:

1. `lookup`: Mapbox geocode → prefer local PostGIS `ST_Contains` on `census_tracts` → Census geocoder fallback.
2. `score_service.build_report_from_scores`: load `neighborhood_scores` by `geoid` + `SCORE_DATA_VINTAGE`.
3. Missing row → HTTP 404 `{"detail":"…","code":"SCORE_UNAVAILABLE"}` — never `build_mock_report` for real IDs.
4. `demo-address-001` mock-only exception for UI tests.
5. Redis report keys `report:{vintage}:{address_id}`; scoring worker best-effort `SCAN` delete after upsert.

**Rationale**: FR-014/017; constitution III + VIII.

---

## 10. Compose operator UX

**Decision**: Baseline order remains `worker-census` → `worker-epa` → `worker-cms` → `worker-scoring`. Reopen adds:

| Phase | Commands (after schema apply) |
|-------|-------------------------------|
| R1 | `worker-fbi` (CDE) → `worker-scoring` |
| R2 | `worker-nces` → `worker-urban` → `worker-scoring` |
| R3 | `worker-acs` → `worker-bls` → `worker-scoring` |

Worker `DATABASE_URL`: `postgresql://postgres:postgres@db:5432/neighborhoodiq`.

---

## 11. Schema application

**Decision**:

- Existing: `infra/sql/init.sql`, `002_raw_ingest_tables.sql`, `003_score_sources.sql`.
- Reopen: add `infra/sql/004_safety_education_economic.sql` (may land as 004a/004b slices) for CDE staging, schools (NCES+Urban), ACS indicators, LAUS series.
- Alembic still deferred for local feature velocity.

---

## 12. Narrative / Claude

**Decision**: Deterministic template narrative from live scores this feature. Claude later. Template may mention dimension provenance lightly when sources leave placeholder—no showcase UI.

---

## 13. Testing strategy

**Decision**:

- Unit: CMS transform; environment resolve; **safety formula** from sample CDE aggregates; **education** join NCESSCH + complementary blend; **economic** ACS+LAUS blend; CDE client parse failures.
- API: assert `sources.safety|education|economic.source_id` after each phase (mocked or Compose).
- Manual: quickstart V1–V6 (MVP) + V7–V9 (R1–R3); Bentonville ±0 vs DB per phase.

---

## 14. Deferred sources (explicit)

Still **not** 002 acceptance:

| Source | Probe status | Why deferred |
|--------|--------------|--------------|
| FEMA NRI | Verified Bentonville | FR-013; hazards later |
| Open-Meteo full climate archive | Ready | AQ fallback already in scoring |
| HUD FMR / Census BFS | Probed | Not selected for R3 (ACS+LAUS only) |
| Zillow / Redfin | Probed | FR-013 private listing markets |
| EJScreen, USDA Atlas, OSM, HPMS, SLD | Probed | Amenities backlog |
| NPPES full dump | Probed | Healthcare geocode enrichment later |

---

## 15. Secrets checklist (env)

| Variable | Used by | Notes |
|----------|---------|--------|
| `DATABASE_URL` | all workers + API | Compose `@db:5432`; host pytest `@localhost:5433` |
| `EPA_AQS_EMAIL` / `EPA_AQS_KEY` | worker-epa | Required for FR-002 |
| `MAPBOX_TOKEN` | API geocode | Lookup path |
| `SCORE_DATA_VINTAGE` | API | Default `2026-Q3` |
| `FBI_CDE_API_KEY` | worker-fbi (R1) | api.data.gov; **required for safety phase** |
| `FBI_CDE_*` optional knobs | worker-fbi | Chart detail, offenses, distance — probe guide |
| `CENSUS_API_KEY` | worker-acs (R3) | Recommended for ACS API quota |
| BLS registration / key | worker-bls (R3) | Per BLS Public Data API v2 rules |
| `HUDUSER_TOKEN` | — | Not 002 |

Never commit secrets; keep `.env` gitignored.

---

## 16. Education phase (R2) — NCES + Urban Institute

### 16a. Complementary field split (probe-informed)

| Source | Keep for scoring | Do not duplicate from the other |
|--------|------------------|----------------------------------|
| **NCES EDGE** (`nces_school_data`) | `NCESSCH`, lat/lon geometry, `LOCALE`, county FIPS (`CNTY`/`STFIP`), name/address — **authoritative locations** | Don’t store conflicting enrollment if Urban has FTE/enrollment |
| **Urban CCD** (`urban_school_data`) | Join on `ncessch`; `enrollment`, `teachers_fte`, `school_level`/`type`/`status`, charter/magnet/virtual flags | Don’t re-derive coordinates if NCES geometry exists |

**Decision**: Ingest **both** into separate tables; join on `NCESSCH`/`ncessch`. Fixture filter: schools in fixture states/counties (NCES county fields + Urban state pull filtered).

### 16b. Education score formula (tract)

**Decision** (blend; tune constants in implementation tests):

1. **Access (NCES, ~55%)**: From tract centroid, distance to nearest public school(s) and optional count within 3 miles → band score (nearby → higher). Locale code can slight-modulate (not as a hard urban/rural penalty that steers).
2. **Capacity/staffing (Urban, ~45%)**: For nearest matched school(s), use pupil–teacher proxy (`enrollment / teachers_fte` when both present) mapped to 0–100 (moderate ratios better than extreme overcrowding or missing FTE). Charter/magnet/virtual are provenance/detail only unless a documented quality signal is verified—default **do not** hard-boost magnet/charter.
3. If one source missing for a tract’s nearest school: score with the available component + reduce confidence in provenance (`reason=partial_nces` | `partial_urban`); do **not** claim dual-success. If both missing: default **50.0** + provenance (not silent placeholder 70).
4. Provenance: `{ "source_id": "nces_urban", "contributors": ["nces_school_data","urban_school_data"], "reason": "…" }`.

**Rationale**: Spec FR-008b + user intent to explore complementary catalogs.

---

## 17. Economic phase (R3) — Census ACS + BLS LAUS

### 17a. Field split

| Source | Grain | Signals for scoring |
|--------|-------|---------------------|
| **Census ACS 5-year** | Prefer **tract** pulls for fixture counties (`for=tract:*&in=state:+county:`); ZCTA OK as fallback if tract vars blocked | Median household income (`B19013_001E`), employment snapshot vars (e.g. `B23025_*` labor force / unemployed share) — document final var list in code |
| **BLS LAUS** | **County** series `LAUCN{ss}{ccc}000000003` (unemployment rate) | Latest (or trailing 12-month mean) unemployment rate for each fixture county |

**Complementary rule**: ACS supplies socio / income / employment structure at tract; LAUS supplies official **county unemployment** time series—do not treat ACS unemployment estimate and LAUS rate as additive doubles; weight LAUS as the unemployment component and ACS as income/socio component.

### 17b. Economic score formula (tract)

**Decision**:

1. **Income component (ACS, ~60%)**: Map median HH income relative to national or fixture-set distribution → 0–100 (document breakpoints).
2. **Labor component (LAUS, ~40%)**: Map county unemployment rate → 0–100 (lower unemployment → higher score); apply that county value to all tracts in the county.
3. Combine weighted average; clamp 0–100.
4. Missing ACS row: derive from county ACS aggregate if available, else partial. Missing LAUS: use ACS labor vars only with `reason=partial_acs`. Both missing → default **50.0**.
5. Provenance: `{ "source_id": "acs_bls_laus", "contributors": ["census_acs","bls_laus"], … }`.

**Rationale**: Spec FR-008c; probe maps ACS as socio core and LAUS as county labour.

**Alternatives considered**: ACS-only (rejected); HUD FMR primary (rejected); Zillow (rejected — FR-013).
