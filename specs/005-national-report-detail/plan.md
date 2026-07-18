# Implementation Plan: National Report Detail Ingest

**Branch**: `005-national-report-detail` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-national-report-detail/spec.md` (clarify session locked).

## Summary

Extend production schema docs and the **national ingest path** so report expand detail (FEMA NRI, CMS Timely, ACS population, `score_detail` re-score) fills **without force** on states that already have base ingest. Prefer those states in `max_states` selection, then virgin states. Operator gate: merge → `dev` → `master`, apply `007`, Azure smoke (`INGEST_SCOPE=smoke`), then National Ingest.

**Approach**: Reuse 004 workers (`ingest.fema`, `ingest.cms_timely`, scoring `score_detail`); lift national refuse; add inventory/status/ACA jobs + ACS pop checkpoint; document Azure runbook.

## Technical Context

**Language/Version**: Python 3.12 (workers); docs Markdown

**Primary Dependencies**: Existing workers stack (psycopg2, Compose/ACA jobs); GitHub Actions national-ingest workflow (env only — no new inputs required)

**Storage**: PostgreSQL — apply `infra/sql/007_report_detail.sql` (+ ensure `acs_indicators.total_population`); tables from 004

**Testing**: pytest under `workers/tests/` (inventory selection, ACS checkpoint, scope allow national); docs checklist for Azure smoke

**Target Platform**: Azure Container Apps Jobs + Azure Postgres (prod); local Compose optional for unit/dev only

**Project Type**: Monorepo — `workers/`, `infra/`, `docs/`, `.github/workflows/`

**Performance Goals**: Gap-aware skips; national FEMA/timely bounded by `INGEST_STATE_BATCH` / orchestrator state units

**Constraints**: No force required for report-detail backfill; do not redo finished base workers; prefer base-complete report-detail gaps in state selection; smoke gate is Azure/prod after promote

**Scale/Scope**: 50 states + DC national path; smoke = Benton County / Bentonville pin

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodInsight Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**: Workers + infra SQL + Azure ACA Jobs + GHA only
- [x] **II. Thin Client, Fat API**: No web/API logic changes required (004 already maps `score_detail`); ops/docs only for report surface
- [x] **III. Precomputed Data Path**: FEMA/Timely/ACS/scoring remain batch workers; API still reads precomputed rows
- [x] **IV. API Contracts & Versioning**: Unchanged report contract from 004
- [x] **V. Security & Secrets**: No new secrets; public FEMA/CMS sources
- [x] **VI. Test Alongside Features**: Worker unit tests for inventory priority, ACS done-check, national scope
- [x] **VII. Observability & Graceful Degradation**: Extend `ingest.status` JOB_NAMES; Workbook still works; missing hazard/wait → limited data
- [x] **VIII. Clear User-Facing Errors**: Worker refuse messages stay clear when misconfigured; report limited-data unchanged

**Post-design re-check**: Gates still pass; no Complexity Tracking rows.

## Project Structure

### Documentation (this feature)

```text
specs/005-national-report-detail/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── national-orchestrator.md
│   └── azure-ops.md
└── tasks.md          # /speckit-tasks
```

### Source Code (touch list)

```text
infra/sql/007_report_detail.sql          # already exists — document apply on Azure
docs/azure-setup-and-cicd.md             # §16 schema, jobs, smoke→national
specs/003-national-ingest/quickstart.md  # optional cross-link / order update
workers/ingest/geo/scope.py              # allow national for fema/cms_timely
workers/ingest/fema/run.py
workers/ingest/cms_timely/run.py
workers/ingest/checkpoints.py            # ACS pop; fema/timely/score_detail helpers
workers/ingest/acs/run.py                # use tightened ACS done-check
workers/ingest/inventory.py              # pipeline + priority selection
workers/ingest/orchestrate/run.py        # ACA job map (if hard-coded elsewhere)
workers/ingest/status.py                 # JOB_NAMES + % for fema/timely/detail
workers/tests/…                          # new/updated unit tests
.github/workflows/national-ingest.yml    # only if job names need env; likely no change
docker-compose.yml                       # already has worker-fema / worker-cms-timely
```

**Structure Decision**: Extend existing national orchestrator/inventory; do not invent a parallel national path.

## Complexity Tracking

> No constitution violations requiring justification.
