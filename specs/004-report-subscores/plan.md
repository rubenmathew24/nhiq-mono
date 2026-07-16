# Implementation Plan: Report Sub-Scores & Category Detail

**Branch**: `004-report-subscores` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-report-subscores/spec.md`. User lock: **dev/local only** with **`smoke` + `metro_10`** geography (not national).

## Summary

Upgrade the **local/dev report** so each of the five score categories shows **sub-scores** and can **expand in place** for concrete stats (nearest ER, schools, crime vs state, AQI, income/unemployment, plus flood/hazard and ER wait when collected).

**Technical approach**:

1. Additive `neighborhood_scores.score_detail` JSONB written by the scoring worker (precomputed sub-scores + expand stats).
2. New local workers: **FEMA NRI** (tract hazard) and **CMS Timely** (ER wait measures), scoped via `active_county_fips()` for `smoke` / `metro_10` only.
3. Extend FastAPI report model + thin Next.js accordion UI on the existing score breakdown card.
4. No Azure national jobs; no NPPES/Zillow.

Probe recipes: sibling `nhiq/backend/scripts/` (FEMA ArcGIS, CMS Timely catalog).

## Technical Context

**Language/Version**: Python 3.12 (workers + FastAPI); TypeScript / Next.js 14 (report UI only)

**Primary Dependencies**: Existing worker stack (`httpx`, `psycopg2`, dotenv); FastAPI + Pydantic; Next.js + Tailwind; Compose PostGIS 16 + Redis

**Storage**: PostgreSQL — additive `score_detail` on `neighborhood_scores`; new `fema_nri_tracts`, `hospital_timely_measures`. Redis report cache invalidate after re-score

**Testing**: `workers/tests/` formulas + transforms; `apps/api/tests/` report shape; `apps/web/src/__tests__/` accordion/affordance; manual Compose quickstart (smoke → metro_10)

**Target Platform**: Local Docker Compose developer machines only

**Project Type**: Monorepo — `workers/ingest`, `workers/scoring`, `apps/api`, `apps/web`

**Performance Goals**: Report remains a single precomputed read; metro_10 re-score completes in one operator session after ingest

**Constraints**: `INGEST_SCOPE` smoke|metro_10 for new workers; no request-time government APIs; Fair Housing–neutral safety copy; additive migrations only

**Scale/Scope**: ~1 county (smoke) or ~10 fixture counties (metro_10); five categories × sub-scores + expand stats; two new Compose worker profiles

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodIQ Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**: Next.js / FastAPI / PostGIS / Redis / workers under existing trees
- [x] **II. Thin Client, Fat API**: Sub-score math and detail assembly in scoring worker + API `score_service`; web only renders
- [x] **III. Precomputed Data Path**: FEMA/Timely ingest → score job writes `score_detail`; report serves DB/Redis
- [x] **IV. API Contracts & Versioning**: Extend `/api/v1/score/{address_id}` payload additively (`sub_scores`); no new version prefix
- [x] **V. Security & Secrets**: No new secrets required for FEMA ArcGIS public layer; CMS Provider Data public; existing DB/Mapbox/EPA/FBI keys unchanged
- [x] **VI. Test Alongside Features**: Formula, API, and web tests planned
- [x] **VII. Observability & Graceful Degradation**: Missing NRI/timely → air-only / access+quality-only with unavailable stats; structured worker logs
- [x] **VIII. Clear User-Facing Errors**: Unavailable hazard/wait copy; `SCORE_UNAVAILABLE` unchanged

**Post-design re-check (2026-07-16)**: Gates still pass. Detail JSONB + raw tables keep request path free of government calls.

## Project Structure

### Documentation (this feature)

```text
specs/004-report-subscores/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── score-api.md
│   └── worker-cli.md
└── tasks.md             # /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
apps/web/src/components/report/   # ScoreBreakdown accordion
apps/web/src/types/api.ts         # SubScore types
apps/api/app/schemas/score.py     # Pydantic SubScore
apps/api/app/services/score_service.py
workers/ingest/fema/              # NEW NRI tract ingest
workers/ingest/cms_timely/        # NEW timely measures
workers/scoring/                  # score_detail + sub-score blends
infra/sql/007_report_detail.sql   # score_detail + new tables (number may adjust)
docker-compose.yml                # worker-fema, worker-cms-timely profiles
```

**Structure Decision**: Follow monorepo conventions; mirror existing `ingest/{cms,fbi}/` worker pattern.

## Complexity Tracking

> No constitution violations requiring justification.
