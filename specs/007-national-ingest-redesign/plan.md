# Implementation Plan: National Ingest Redesign

**Branch**: `007-national-ingest-redesign` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-national-ingest-redesign/spec.md`

## Summary

Make nationwide ingest finishable and trustworthy: fix inflated progress denominators; replace per-county/per-district remote loops with bulk files or state-wide queries where automated and fidelity-preserving (FEMA NRI CSV, ACS `county:*`, Urban `?fips=`); speed FBI via agency-list caching + bounded concurrency; batch many gap states per ACA execution; run continuous orchestrator cycles (GH Action self-chain or PowerShell loop) until 50+DC inventory is clear.

## Technical Context

**Language/Version**: Python 3.12 (workers)

**Primary Dependencies**: httpx, psycopg2, pandas/`csv`+`zipfile` for FEMA bulk, concurrent.futures, Azure CLI / ACA Jobs, GitHub Actions

**Storage**: PostgreSQL + PostGIS (`geo_counties`, raw ingest tables, `neighborhood_scores`, `ingest_status_snapshot`)

**Testing**: pytest under `workers/tests/`

**Target Platform**: Azure Container Apps Jobs + GitHub Actions; local PowerShell coordinator

**Project Type**: Monorepo workers / ops orchestration

**Performance Goals**: ≥50% wall-clock reduction vs prior “max 5 states × sequential workers” pattern for comparable gap sets; continuous unattended completion of 50+DC

**Constraints**: ACA replica timeouts (orchestrator ≤6h, workers ≤3h); GHA job ≤6h with self-redispatch; FBI CDE rate limits; no manual browser downloads; preserve FBI per-county agency methodology

**Scale/Scope**: ~3,143 counties / ~74k tracts; 11 pipeline workers + scoring; continuous until inventory clear

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodIQ Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**: Workers + GHA + ACA only; no alternate stack
- [x] **II. Thin Client, Fat API**: No web/API product changes required
- [x] **III. Precomputed Data Path**: Still batch ingest → scoring → DB; user requests unchanged
- [x] **IV. API Contracts & Versioning**: N/A for public HTTP API (ops env contracts only)
- [x] **V. Security & Secrets**: Existing Key Vault / SP patterns; no new secrets in images
- [x] **VI. Test Alongside Features**: pytest for status denominator, bulk/wide fetch, orchestrator batching
- [x] **VII. Observability & Graceful Degradation**: Orchestrator cycle markers + status snapshots; checkpoint resume
- [x] **VIII. Clear User-Facing Errors**: Fail-closed empty registry / bulk URL failures with clear logs

## Project Structure

### Documentation (this feature)

```text
specs/007-national-ingest-redesign/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── worker-env.md
│   └── continuous-orchestrator.md
└── tasks.md
```

### Source Code (repository root)

```text
workers/ingest/status.py
workers/ingest/fema/{run,client,transform}.py
workers/ingest/acs/{run,client}.py
workers/ingest/urban/{run,client}.py
workers/ingest/fbi/{run,client}.py
workers/ingest/epa/{run,client}.py
workers/ingest/bls/{run,client}.py
workers/ingest/cms_timely/run.py
workers/ingest/orchestrate/{run,azure_jobs}.py
workers/ingest/inventory.py
.github/workflows/national-ingest.yml
scripts/national-ingest.ps1
docs/azure-setup-and-cicd.md
workers/tests/
```

**Structure Decision**: Extend existing national ingest workers and orchestrator; no new top-level apps.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
