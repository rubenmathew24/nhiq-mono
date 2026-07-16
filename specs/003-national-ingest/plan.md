# Implementation Plan: National Ingest

**Branch**: `003-national-ingest` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-national-ingest/spec.md`

## Summary

Enable ops to load **50 states + DC** county data in **explicit state batches**, with **DB-backed skip-done checkpoints** on every worker, **FBI agency selection via county centroids**, and a **real `INGEST_SCOPE=national` status denominator**. Keep `smoke` / `metro_10` fixture paths. Territories stay out of v1 but share an extensible jurisdiction list.

**Orchestrator (US5):** Inventory gaps per worker from Postgres; ACA job `niq-worker-orchestrate` starts only incomplete worker/state pairs (per-state pipeline order). Thin GitHub Actions `workflow_dispatch` triggers the orchestrator—not Deploy-on-master.

## Technical Context

**Language/Version**: Python 3.12 (workers)

**Primary Dependencies**: Existing worker stack (psycopg2, geopandas/shapely, requests); Azure ACA Jobs + Postgres

**Storage**: PostgreSQL 16 + PostGIS (`geo_counties` registry + existing ingest/score tables)

**Testing**: pytest under `workers/tests/`

**Target Platform**: Docker worker image; Azure Container Apps Jobs (`niq-worker-*`)

**Project Type**: Batch workers + ops status (no product API/UI change required)

**Performance Goals**: One small state batch completable within ACA replica timeout with restarts; national % updates after each batch

**Constraints**: ACA ~7200s timeout; national runs **require** `INGEST_STATE_BATCH`; no all-51 unattended run in v1

**Scale/Scope**: ~3,143 counties (50+DC); phased by state FIPS batch

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Locked Stack & Monorepo**: Workers + `infra/sql` only; no new frameworks
- [x] **II. Thin Client, Fat API**: No web/API business logic changes
- [x] **III. Precomputed Data Path**: Still ingest → score → API reads precomputed rows
- [x] **IV. API Contracts & Versioning**: N/A (no public API change)
- [x] **V. Security & Secrets**: Existing Key Vault / env keys; no new secrets in repo
- [x] **VI. Test Alongside Features**: pytest for scope, batch rejection, checkpoints, national status
- [x] **VII. Observability & Graceful Degradation**: Structured skip/fetch logs; honest partial FBI coverage
- [x] **VIII. Clear User-Facing Errors**: Clear RuntimeError when national batch missing / invalid state FIPS

## Project Structure

### Documentation (this feature)

```text
specs/003-national-ingest/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── worker-env.md
└── tasks.md
```

### Source Code (touched)

```text
infra/sql/006_geo_counties.sql
workers/ingest/geo/           # jurisdictions, scope resolution, county registry load
workers/ingest/checkpoints.py # shared “is county done?” helpers
workers/ingest/inventory.py   # gap inventory JSON
workers/ingest/orchestrate/   # ACA orchestrator
workers/ingest/*/run.py       # use scope + checkpoints
workers/ingest/fbi/run.py     # centroids / geo_counties points
workers/ingest/status.py      # real national denominators
workers/scoring/compute.py    # national batch counties
.github/workflows/national-ingest.yml
docs/azure-setup-and-cicd.md  # national runbook
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| New `geo_counties` table | National FBI needs centroids; status needs stable universe | Deriving only from tracts couples universe to census completion and lacks centroids before tracts exist |

## Phase 0 / Phase 1

See [research.md](./research.md), [data-model.md](./data-model.md), [contracts/worker-env.md](./contracts/worker-env.md), [quickstart.md](./quickstart.md).
