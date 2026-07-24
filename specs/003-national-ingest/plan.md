# Implementation Plan: National Ingest

**Branch**: `003-national-ingest` | **Date**: 2026-07-23 (consolidated) | **Spec**: [spec.md](./spec.md)

**Input**: Consolidated feature specification (original 003 + absorbed 005 report-detail + 007 redesign).

## Summary

As-built national ops path: **50 states + DC** via `geo_counties`; **explicit state batches** + **DB skip-done checkpoints**; **inventory orchestrator** (ACA + GHA) with **class A/B report-detail priority**; **Azure smoke gate** before trusting expand; **honest status %** (full registry, scoring county-grain); **continuous** completion (GHA chain / PowerShell) with **multi-state batching**; **bulk/wide fetches** (FEMA NRI CSV, ACS `county:*`, Urban `?fips=`, FBI cache+concurrency, EPA/BLS bulk flags). Preserve **smoke** / **metro_10**. Score formulas and fixture product path remain in **002**; expand UI in **004**.

## Technical Context

**Language/Version**: Python 3.12 (workers)

**Primary Dependencies**: httpx/requests, psycopg2, pandas/csv+zipfile (FEMA), concurrent.futures, Azure ACA Jobs, GitHub Actions, PowerShell

**Storage**: PostgreSQL + PostGIS (`geo_counties`, raw ingest, `neighborhood_scores` / `score_detail`, `fema_nri_tracts`, `hospital_timely_measures`, `ingest_status_snapshot`)

**Testing**: pytest under `workers/tests/`

**Target Platform**: Azure Container Apps Jobs + GitHub Actions; local PowerShell coordinator; Docker Compose for metro/smoke

**Performance Goals**: ≥50% wall-clock reduction vs prior max-5 sequential pattern; continuous unattended 50+DC completion

**Constraints**: ACA timeouts (orchestrator 21600s, workers 10800s); GHA ≤6h with self-redispatch; FBI CDE rate limits; no manual FBI master downloads; national workers require `INGEST_STATE_BATCH`

**Scale/Scope**: ~3,143 counties / ~74k tracts; 11 pipeline workers + scoring

## Constitution Check

- [x] **I. Locked Stack & Monorepo**: Workers + GHA + ACA only
- [x] **II. Thin Client, Fat API**: No product web/API changes required for national ops (004 owns expand UI)
- [x] **III. Precomputed Data Path**: Batch ingest → scoring → DB
- [x] **IV. API Contracts & Versioning**: Ops env contracts only
- [x] **V. Security & Secrets**: Existing Key Vault / SP patterns
- [x] **VI. Test Alongside Features**: pytest for status, inventory, bulk/wide, continuous, report-detail checkpoints
- [x] **VII. Observability & Graceful Degradation**: Snapshots, cycle markers, checkpoint resume
- [x] **VIII. Clear User-Facing Errors**: Fail-closed registry; clear batch/bulk failures

## Project Structure

### Documentation (this feature)

```text
specs/003-national-ingest/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── worker-env.md
│   ├── continuous-orchestrator.md
│   ├── azure-ops.md
│   └── national-orchestrator.md
└── tasks.md
```

### Source Code (as-built touch list)

```text
infra/sql/006_geo_counties.sql
infra/sql/007_report_detail.sql
workers/ingest/geo/
workers/ingest/checkpoints.py
workers/ingest/inventory.py
workers/ingest/force.py
workers/ingest/status_pulse.py
workers/ingest/status.py
workers/ingest/orchestrate/
workers/ingest/{fema,cms_timely,acs,urban,fbi,epa,bls,*/run.py}
workers/scoring/compute.py
.github/workflows/national-ingest.yml
scripts/national-ingest.ps1
docs/azure-setup-and-cicd.md
workers/tests/
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| `geo_counties` table | National FBI needs centroids; status needs stable universe | Deriving only from tracts couples universe to census completion |
| Continuous GHA self-chain | Platform time limits | Manual ≤5-state re-triggers cannot finish nation |

## Phase artifacts

See [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md), [tasks.md](./tasks.md) (completed archive).
