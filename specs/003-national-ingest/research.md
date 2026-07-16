# Research: National Ingest

## R1 — County universe source

**Decision**: Persist counties from Census TIGER **county** shapefiles (`tl_2023_{state}_county.zip`) into `geo_counties` (FIPS, name, centroid lon/lat, INTPT if present).

**Rationale**: Same family as existing tract TIGER URLs; provides centroids before tract load; queryable for status denominators.

**Alternatives rejected**: Static checked-in 3k-row CSV (stale); derive only from `census_tracts` (no centroids, chicken-and-egg with census worker).

## R2 — Jurisdiction extensibility

**Decision**: Single frozenset/list `INCLUDED_STATE_FIPS` = 50 states + `11` (DC). Separate `TERRITORY_STATE_FIPS` (empty in v1: PR `72`, GU `66`, VI `78`, AS `60`, MP `69` documented). National universe = counties whose state FIPS ∈ `INCLUDED_STATE_FIPS`. Adding territories later = move codes into included set and load their TIGER county files.

## R3 — Batch control

**Decision**: Env `INGEST_STATE_BATCH` = comma-separated 2-digit state FIPS. Required when `INGEST_SCOPE=national`. Reject start if missing/empty/unknown codes. `INGEST_COUNTY_ALLOWLIST` may further narrow within the batch (and within fixtures for metro/smoke).

**Rationale**: Prevents accidental all-US job under 7200s ACA timeout.

## R4 — Scope resolution

**Decision**:

| `INGEST_SCOPE` | Counties |
|----------------|----------|
| `smoke` | `{05007}` (existing) |
| `metro_10` | fixture set (+ optional allowlist ∩ fixtures) |
| `national` | counties from `geo_counties` where `state_fips ∈ INGEST_STATE_BATCH` ∩ included jurisdictions |

Workers call one helper instead of `fixture_county_fips()` when national.

## R5 — Checkpoints

**Decision**: DB-as-truth. Shared helpers: e.g. `counties_with_census_tracts`, `counties_with_crime_agencies`, etc. matching status metrics. Each worker: for unit in scope → if done → `skip_checkpoint` log → else fetch/upsert.

**Rationale**: Matches FBI per-county upsert pattern already in repo.

## R6 — FBI national points

**Decision**: For national (and optionally anytime `geo_counties` has the county), use `(centroid_lat, centroid_lon)` + county name/state abbr from registry. Metro/smoke may keep fixture addresses when registry row missing.

## R7 — Status national

**Decision**: Denominator = `COUNT(*)` from `geo_counties` for included jurisdictions (all 50+DC once registry fully loaded). If registry incomplete, denominator = current registry count and detail notes `registry_incomplete`. Remove `national_not_supported` stub.

**Note**: Operator must run a one-time (or per-state) **geo/county registry** load for all included states (or at least batch states) before % is meaningful. Plan: `python -m ingest.geo.run` loads TIGER counties for `INGEST_STATE_BATCH` (or all included if `INGEST_GEO_LOAD_ALL=1` for registry bootstrap only — prefer batch-only for ACA; document a loop over states for full registry).

**Refined**: For full national denominator, support `INGEST_STATE_BATCH=*` or dedicated `ingest.geo.run` with `INGEST_GEO_LOAD_ALL=1` that only loads county registry (lightweight vs tracts). Default geo job still requires batch OR load-all flag.
