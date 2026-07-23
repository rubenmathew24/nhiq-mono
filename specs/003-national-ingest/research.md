# Research: National Ingest

**Feature**: `003-national-ingest` | **Consolidated**: 2026-07-23 (absorbs former 005 + 007 research)

## Current decisions

### R1 — County universe source

**Decision**: Persist counties from Census TIGER **county** shapefiles (`tl_2023_{state}_county.zip`) into `geo_counties` (FIPS, name, centroid lon/lat, INTPT if present).

**Rationale**: Same family as tract TIGER URLs; provides centroids before tract load; queryable for status denominators.

**Alternatives rejected**: Static checked-in 3k-row CSV (stale); derive only from `census_tracts` (no centroids, chicken-and-egg with census worker).

### R1a — Tract land/water area (2026-07-23)

**Decision**: National census path keeps TIGER `ALAND`/`AWATER` on `census_tracts` (same as 002 FR-004a). Water-only tracts stay in the warehouse; Discover filters presentation (`aland = 0`). Status/scoring denominators unchanged.

**Rationale**: One schema for smoke / metro_10 / national; Lake Michigan–style tracts otherwise pollute city maps/summaries without being “gaps” in national ingest.

**Alternatives rejected**: Separate “display tracts” table; deleting water-only rows (breaks FEMA/score grain); ACS population as national census requirement for this amend.

### R2 — Jurisdiction extensibility

**Decision**: `INCLUDED_STATE_FIPS` = 50 states + `11` (DC). Separate `TERRITORY_STATE_FIPS` (empty in v1: PR `72`, GU `66`, VI `78`, AS `60`, MP `69` documented). National universe = counties whose state FIPS ∈ `INCLUDED_STATE_FIPS`.

### R3 — Batch control

**Decision**: Env `INGEST_STATE_BATCH` = comma-separated 2-digit state FIPS. Required when `INGEST_SCOPE=national`. Reject start if missing/empty/unknown codes. `INGEST_COUNTY_ALLOWLIST` may further narrow within the batch.

**Rationale**: Prevents accidental all-US job under ACA timeout. Orchestrator may set multi-state batches (`ORCH_BATCH_STATES`).

### R4 — Scope resolution

| `INGEST_SCOPE` | Counties |
|----------------|----------|
| `smoke` | `{05007}` |
| `metro_10` | fixture set (+ optional allowlist ∩ fixtures) |
| `national` | counties from `geo_counties` where `state_fips ∈ INGEST_STATE_BATCH` ∩ included jurisdictions |

### R5 — Checkpoints

**Decision**: DB-as-truth. Shared helpers per worker grain. Each worker: for unit in scope → if done → `skip_checkpoint` → else fetch/upsert. Force disables skip-done.

### R6 — FBI national points

**Decision**: For national (and when `geo_counties` has the county), use `(centroid_lat, centroid_lon)` + county name/state abbr from registry. Metro/smoke may keep fixture addresses when registry row missing.

### R7 — Status national (current)

**Decision**: Denominator = `COUNT(*)` from `geo_counties` for included 50+DC. Empty or incomplete registry (distinct included `state_fips` ≠ 51) → **fail closed**. Scoring done at **county** grain: every tract has `fbi_cde` + non-empty `score_detail`. Jobs include `fema` and `cms_timely`. Console snapshot metrics-only; full detail in Postgres.

### R8 — Inventory-driven orchestrator

**Decision**: Inventory + scheduling inside ACA job `niq-worker-orchestrate`. GHA `workflow_dispatch` → start/poll that job. Pipeline:

```text
census → epa → cms → fbi → nces → urban → acs → bls → fema → cms_timely → scoring
```

Skips workers with zero gaps. Exclusive `ORCH_FORCE_STATES` / `ORCH_STATE_FILTER`. Class A (base-complete, report-detail gaps) before class B for normal gap-fill.

### R9 — Report-detail schema and scope lift

**Decision**: Apply additive `infra/sql/007_report_detail.sql` on Azure. Confirm `acs_indicators.total_population`. FEMA / CMS Timely use normal scope resolution (`smoke` | `metro_10` | `national`) — no `assert_dev_scope` refuse. ACA jobs `niq-worker-fema`, `niq-worker-cms-timely`.

### R10 — ACS population without force

**Decision**: County ACS “done” only if tract `acs_indicators` rows exist **and** `total_population IS NOT NULL` (and state-level pop when in scope). Null population remains a normal (non-force) gap.

### R11 — State selection priority (class A/B)

**Decision**: When not force / not exclusive filter-only:

1. Set **A** = base-complete states with any gap in fema | cms_timely | acs-pop | scoring-detail.
2. Set **B** = all other states still needing pipeline work.
3. Order = `sorted(A) + sorted(B - A)`, then apply batch/`max_states` caps.

### R12 — Azure smoke gate

**Decision**: Promote `dev` → `master` → Deploy + worker image → apply schema → Azure smoke (`acs` if pop gap → `fema` → `cms_timely` → `scoring`) → Bentonville expand matches 004 local/dev → only then National Ingest. Compose alone insufficient.

### R13 — Scoring progress denominator

**Decision**: County grain against `|geo_counties|`, not `COUNT(*) FROM census_tracts` for currently loaded counties.

### R14 — FEMA bulk NRI

**Decision**: Download FEMA National Risk Index All Census tracts Table Format (CSV zip) once per run; parse/upsert in-scope tracts. Drop per-county ArcGIS + N+1 checkpoint as primary path. Fallback to ArcGIS if bulk returns non-zip / 403 (`FEMA_NRI_BULK_URL` overridable).

### R15 — ACS / Urban wide fetch

**Decision**: ACS `fetch_state_tract_rows` with `in=state:{SS} county:*`. Urban paginate CCD with `?fips=` + skip-done on `(ncessch, year)`.

### R16 — FBI: no bulk master files

**Decision**: Keep CDE per-county agency + charts; cache `fetch_agencies_by_state`; shared rate limiter + `ThreadPoolExecutor` (`FBI_MAX_CONCURRENCY` default 4).

### R17 — EPA / BLS secondary bulk

**Decision**: Prefer AirData / LAUS flat files; API fallback behind `EPA_USE_BULK_FILES` / `BLS_USE_BULK_FILES` (default on).

### R18 — Continuous orchestration

**Decision**: `ORCH_CONTINUOUS=1` loops inventory → per-worker multi-state batches (`ORCH_BATCH_STATES` default 10) → rebuild; exit `0` complete, `2` time budget with gaps, `1` hard fail. GHA chains executions then self-redispatches (`chain_depth` max 50). PowerShell `scripts/national-ingest.ps1` mirrors loop. Gaps only on exclude → `blocked_excluded`, not complete.

### R19 — Timeouts

**Decision**: Orchestrator ACA `--replica-timeout 21600`; per-source jobs `10800`; Python budget `ORCH_TIME_BUDGET_SECONDS=20700`.

### R20 — CMS Timely skip-done

**Decision**: Skip-done by active `data_vintage` for states that already have measures. Provider-level catalog download skip remains optional/deferred; upserts stay idempotent.

---

## Evolution / superseded

| Former decision | Superseded by |
|-----------------|---------------|
| Single multi-day unattended run out of scope; re-dispatch only (original 003 FR-013) | Continuous mode (R18) — bounded mode retained |
| Scoring % against loaded tracts / tract grain only | County grain vs full `geo_counties` (R7, R13) |
| Incomplete registry: denominator = current registry count + `registry_incomplete` note | Fail closed empty/partial registry (R7, R15 completeness) |
| FEMA/CMS Timely `assert_dev_scope` refuse national | Scope lift (R9) |
| ACS done = row existence only | Require `total_population` (R10) |
| FEMA ArcGIS per-county primary | Bulk NRI CSV zip (R14) |
| Max 5 states sequential manual re-triggers as primary ops model | Continuous + `ORCH_BATCH_STATES` (R18) |

---

## Out of scope

- Product in-app national progress UI / Slack webhooks.
- Re-implementing score formulas / expand UI (004).
- Auto-start national on Deploy.
- Territories in v1 denominators.
- FBI master bulk files requiring manual browser download.
- Laptop-only full national fetch as the primary path.
