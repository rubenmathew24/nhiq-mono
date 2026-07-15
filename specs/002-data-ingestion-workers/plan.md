# Implementation Plan: Data Ingestion Workers

**Branch**: `002-data-ingestion-workers` | **Date**: 2026-07-14 (reopened) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-data-ingestion-workers/spec.md` (including reopen clarifications for safety / education / economic). Design intent from `docs/nhiq-design-main/07-data-ingestion-workers.md` and schema from `docs/nhiq-design-main/08-database-schema.md`. **Data-source ground truth** from probe research in `nhiq/backend/scripts/` (see Research External Source).

## Summary

Stand up **local Docker-only** Python ingestion + scoring workers that populate PostGIS for the **10 fixture addresses’ counties**, then wire FastAPI lookup/score so the local web app can search those addresses and show **live** `neighborhood_scores` (not mock-as-live).

### Already delivered (MVP slice)

Census tracts → EPA AQS → CMS Hospital General Information → scoring (**healthcare** + **environment** with EPA→Open-Meteo fallback + `score_sources`) → live reports. **No Azure Container Apps Jobs, no `master` deploy, no national ingest.**

### Reopen acceptance path (clarified 2026-07-14)

Extend the **same** `002` branch/spec in **three closeable phases** (placeholders remain only for dimensions not yet delivered):

| Phase | Dimension | Sources (required) | Outcome |
|-------|-----------|--------------------|---------|
| **R1** | Safety | FBI CDE chart/agency (`FBI_CDE_API_KEY`) | Replace FBI skeleton; non-placeholder `safety_score` + `score_sources.safety` |
| **R2** | Education | **NCES** + **Urban Institute** | Dual ingest; complementary fields in `education_score` + provenance for both |
| **R3** | Economic | **Census ACS** + **BLS LAUS** | Dual ingest; complementary fields in `economic_score`; Zillow/Redfin still out (FR-013) |

FEMA NRI, source-showcase UI, and Azure Jobs remain out of scope.

**What the probe research implies for reopen phases:**

| Topic | Probe learning | Plan stance |
|-------|----------------|-------------|
| Safety | CDE chart: ≤5 nearest ORIs, offense slugs, state benchmarks; agency grain | Implement full CDE worker in R1; score tracts from county-assigned agency aggregates |
| Education | NCES = schools + coords/locale; Urban = enrollment/FTE/type enrichment via `ncessch` | Both required; join on NCESSCH; don’t double-count the same metric |
| Economic | ACS ZCTA/tract socio core; LAUS county unemployment series | ACS + LAUS both required; publish tract scores with county LAUS component |
| Hazards / Zillow | FEMA verified; Zillow private | Still deferred (FR-013) |

Python stays the worker + API language so future Claude narrative summaries fit the same stack.

### Research external source

Authoritative probe artifacts (sibling repo; not copied into this monorepo):

- `…/nhiq/backend/scripts/DATA_SOURCE_OUTPUT_GUIDE.md` — per-`source_id` production path, geography grain, overlaps
- `…/nhiq/backend/scripts/source_field_notes.json` — field dictionaries (NPPES, NCES, Urban, FEMA NRI, FBI CDE)
- `…/nhiq/backend/scripts/data_probe/{healthcare,crime,environment,education,…}.py` — live harness implementations

Use those documents when detailing ETL for R1–R3; keep monorepo workers thin (patterns/env names, not a full probe vendor).

## Technical Context

**Language/Version**: Python 3.12 (workers + FastAPI API); TypeScript/Next.js only for existing report UI consumption (no score math in the browser)

**Primary Dependencies**: Workers — `httpx`, `psycopg2`, `geopandas`/`pandas`, `python-dotenv`, `tenacity`, `redis`; API — FastAPI, SQLAlchemy async, Redis cache-aside; Compose — `postgis/postgis:16-3.4`, Redis, `web`/`api`/`worker-*` profiles

**Storage**: PostgreSQL 16 + PostGIS via Compose `db`. Raw + score tables in `infra/sql/init.sql` (+ incremental SQL for reopen tables). System of record: `neighborhood_scores` (+ `score_sources` JSONB). Redis: report cache invalidated after scoring

**Testing**: pytest under `workers/tests/` (transforms, formulas, per-phase ingest fakes) and `apps/api/tests/test_score_live.py`; Vitest for unavailable UI; manual Compose quickstart + Bentonville per phase

**Target Platform**: Local Docker Compose on developer machines. Explicitly **not** Azure / production / `master`

**Project Type**: Monorepo batch workers + FastAPI score path + thin Next.js report viewer

**Performance Goals**: Fixture-county prep in one operator session per phase; score job ~5k tracts; report path serves precomputed scores without government API calls

**Constraints**: Fixture-county scope only; secrets in `.env`; mock reports must not masquerade as live; dual-source phases must document complementary field use; `FBI_CDE_API_KEY` required for R1; optional `CENSUS_API_KEY` / BLS registration as needed by ACS/LAUS clients

**Scale/Scope**: 10 addresses → ~10 counties; workers grow: `ingest/{epa,census,cms,fbi,nces,urban,acs,bls}` + `scoring`; phases R1→R2→R3 independently testable

**Implementation status**: Healthcare/environment MVP **done**. Reopen = R1 safety first, then education, then economic on this branch.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodIQ Constitution)*

- [x] **I. Locked Stack & Monorepo**: Python 3.12 workers under `workers/`; FastAPI in `apps/api`; PostGIS via Compose
- [x] **II. Thin Client, Fat API**: Browser only searches/displays; scores assembled server-side
- [x] **III. Precomputed Data Path**: New source workers write raw tables → scoring worker → `neighborhood_scores`; no per-request government crime/school/ACS calls on the report path
- [x] **IV. API Contracts & Versioning**: Keep `/api/v1/lookup` and `/api/v1/score/{address_id}`; extend `sources` map as dimensions leave placeholders
- [x] **V. Security & Secrets**: `EPA_AQS_*`, `MAPBOX_TOKEN`, `DATABASE_URL`, `FBI_CDE_API_KEY`, optional Census/BLS keys from env; never commit
- [x] **VI. Test Alongside Features**: Transform/formula tests per phase + API assertions on `sources.{dimension}`
- [x] **VII. Observability & Graceful Degradation**: Per-unit progress logs; dual-source partial failure documented (no silent fake dual-success)
- [x] **VIII. Clear User-Facing Errors**: `SCORE_UNAVAILABLE` unchanged; missing FBI key fails R1 worker clearly

**Post-design re-check (2026-07-14 reopened)**: Gates still pass. Spec clarifications now authorize FBI CDE / NCES+Urban / ACS+BLS inside **002** (phased). FEMA/Zillow remain excluded.

## Project Structure

### Documentation (this feature)

```text
specs/002-data-ingestion-workers/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── worker-cli.md
│   └── score-api.md
└── tasks.md             # /speckit-tasks after this plan
```

### Source Code (repository root) — target after reopen

```text
workers/
├── ingest/
│   ├── base.py
│   ├── fixtures/                    # addresses, FIPS, weights, placeholders
│   ├── epa/ | census/ | cms/        # MVP (done)
│   ├── fbi/                         # R1: CDE chart ingest (upgrade skeleton)
│   ├── nces/                        # R2: EDGE school locations
│   ├── urban/                       # R2: Urban CCD directory stats
│   ├── acs/                         # R3: Census ACS indicators
│   └── bls/                         # R3: LAUS unemployment
└── scoring/
    ├── formulas.py                  # healthcare/environment + safety/education/economic
    ├── environment.py | open_meteo.py
    ├── safety.py | education.py | economic.py   # (or modules as needed)
    └── compute.py

apps/api/...                         # live score path already serves sources.*
infra/sql/
├── init.sql
├── 002_raw_ingest_tables.sql
├── 003_score_sources.sql
└── 004_safety_education_economic.sql   # R1–R3 schema (may ship in slices)
docker-compose.yml                   # worker-* profiles for new services
.env.example
```

**Structure Decision**: Keep probe harness in sibling repo. Merge target when ready: **`dev` only**.

## Complexity Tracking

| Topic | Why noted | Simpler alternative rejected because |
|-------|-----------|--------------------------------------|
| Open-Meteo at score time | EPA sparsity | Prefetch warehouse later |
| CMS ZIP geocode | Dataset has no coords | Hard-coded hospitals too weak |
| Agency-grain safety → tract scores | Accept CDE reality | Fake tract crime rates without data |
| Dual education sources | Clarified requirement | NCES-only discarded by product |
| Dual economic sources | Clarified requirement | ACS-only discarded by product |
| Phased close on same branch | Clarified delivery | Big-bang all three before any ship |

---

## Delivery order (operators)

1. Keep MVP workers green (census → epa → cms → scoring).
2. **R1**: schema for CDE staging → `worker-fbi` CDE load → safety formulas → rescore → Bentonville safety ≠ placeholder.
3. **R2**: schools tables → `worker-nces` + `worker-urban` → education formulas → rescore.
4. **R3**: ACS + LAUS tables → workers → economic formulas → rescore → all five dimensions source-backed for fixtures.

## Phase 2

Planning artifacts below; regenerate tasks with `/speckit-tasks` prioritizing R1 safety.
