# Research: National Ingest Redesign

## R1 — Scoring progress denominator

**Decision**: Count scoring done at **county** grain against `|geo_counties|` for 50+DC (same as inventory `counties_with_score_detail`), not `COUNT(*) FROM census_tracts` for currently loaded counties.

**Rationale**: Loaded-tract denominator inflates % when only a minority of states exist in `census_tracts`. Spec SC-001 / FR-001–002.

**Alternatives considered**: Fixed national tract count table (no registry); leave tract grain with incomplete census (rejected — dishonest progress).

## R2 — FEMA: bulk NRI vs ArcGIS per county

**Decision**: Download FEMA National Risk Index **All Census tracts** Table Format (CSV zip) once per run; parse and upsert in-scope tracts. Drop per-county ArcGIS + per-county checkpoint N+1.

**Rationale**: ~3,143 remote queries → one file (~40–400MB). OpenFEMA/fema.gov publishes automatable downloads (v1.20+).

**Alternatives considered**: Concurrent ArcGIS only (still thousands of calls); county-level NRI file (loses tract hazards for expand UI).

## R3 — ACS: per-state wildcard

**Decision**: `fetch_state_tract_rows` with `in=state:{SS} county:*`; filter to pending counties before upsert.

**Rationale**: Census API already supports it; cuts ~62 calls/state to 1.

**Alternatives considered**: ThreadPool of per-county calls (still N calls); ACS bulk FTP (more format churn).

## R4 — Urban: per-state fips filter + skip-done

**Decision**: Paginate CCD directory with `?fips=` (comma-separated states); skip schools already in `schools_urban` for active year.

**Rationale**: Documented Urban Education Data Portal filter; replaces thousands of LEAID calls.

**Alternatives considered**: NCES CCD zip bulk (JS-only download page, unstable URLs); keep LEAID loop + concurrency only.

## R5 — FBI: no bulk master files

**Decision**: Keep CDE per-county agency + charts; cache `fetch_agencies_by_state`; shared rate limiter + `ThreadPoolExecutor` for counties.

**Rationale**: Master NIBRS zips need manual browser download (`robots.txt` Forbidden). BJS national estimates change methodology/granularity.

**Alternatives considered**: Switch to BJS estimates (rejected — fidelity); manual master file ops step (fails “one button / automated”).

## R6 — EPA / BLS secondary bulk

**Decision**: Prefer EPA AirData pre-generated parameter zips and BLS LAUS flat files; keep API fallback behind `EPA_USE_BULK_FILES` / `BLS_USE_BULK_FILES` (default on).

**Rationale**: Not top bottlenecks but remove unnecessary API volume; flags hedge format breakage.

## R7 — Continuous orchestration

**Decision**: `ORCH_CONTINUOUS=1` loops inventory → per-worker multi-state batches (`ORCH_BATCH_STATES` default 10) → rebuild; exit `0` nation complete, `2` time budget with gaps, `1` hard fail. GHA chains executions then self-redispatches (`chain_depth` max 50). PowerShell mirrors loop.

**Rationale**: GHA ≤6h, ACA orchestrator hard max 24h (use 6h); prior max_states=5 sequential design cannot finish the nation.

**Alternatives considered**: Five parallel ACA executions per worker (env PATCH races + rate-limit chaos); laptop-only full fetch (secrets/API keys duplicated, diverges from prod path).

## R8 — Timeouts

**Decision**: Orchestrator ACA `--replica-timeout 21600`; per-source jobs `10800`; orchestrator Python budget `ORCH_TIME_BUDGET_SECONDS=20700`.

**Rationale**: Exit code 2 before Azure kills the container; workers fit multi-state FBI batches post-speedup.
