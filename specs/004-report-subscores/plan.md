# Implementation Plan: Report Sub-Scores & Category Detail

**Branch**: `004-report-subscores` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-report-subscores/spec.md`. User lock: **dev/local only** with **`smoke` + `metro_10`** geography (not national).

**Revision**: Post-implement UX polish (2026-07-16 explore notes) — plain-English expand, interactive category boxes, schools-by-level, ER wait tone fix. Core ingest/schema from the first plan remains shipped; this plan delta focuses on `score_detail` rewrite + web affordance.

## Summary

Upgrade the **local/dev report** so each of the five score categories shows **sub-scores** and can **expand in place** from an **obvious interactive box** for concrete, glanceable stats.

**Already delivered (first implement)**: `score_detail` JSONB; FEMA NRI + CMS Timely workers (smoke/metro_10); API `sub_scores` + factors; accordion UI.

**Polish delta (this re-plan)**:

1. **Web**: Category boxes (bordered/surface controls); color expand values with ScoreBar tiers when `tone_score` / mapped impact is present; drop reliance on “View details” microcopy.
2. **Scoring `detail.py` (+ compute joins)**: Ordinal ER labels; fix timeliness tone vs state/national; plain-English safety labels + condensed agency/grain; AQI without source id; schools nearest-by-level; drop PTR/locale; employment rate from ACS; staffing sub-score limited-data.
3. **Tests + re-score** smoke (and metro_10 as needed) so Bentonville fixture matches SC-008/SC-009.
4. No new Azure national jobs; no NPPES/Zillow; no school-zoning ingest.

## Technical Context

**Language/Version**: Python 3.12 (workers + FastAPI); TypeScript / Next.js 14 (report UI only)

**Primary Dependencies**: Existing worker stack (`httpx`, `psycopg2`, dotenv); FastAPI + Pydantic; Next.js + Tailwind; Compose PostGIS 16 + Redis

**Storage**: PostgreSQL — existing `score_detail` on `neighborhood_scores`; existing `fema_nri_tracts`, `hospital_timely_measures`, `schools_*`, `acs_indicators`. Polish rewrites JSON only (no new tables)

**Testing**: `workers/tests/` detail labels + timeliness tone; `apps/api/tests/` factor shape; `apps/web/src/__tests__/` category box affordance + tone classes; manual Compose quickstart

**Target Platform**: Local Docker Compose developer machines only

**Project Type**: Monorepo — `workers/ingest`, `workers/scoring`, `apps/api`, `apps/web`

**Performance Goals**: Report remains a single precomputed read; smoke re-score after polish is seconds–minutes

**Constraints**: `INGEST_SCOPE` smoke|metro_10 for new workers; no request-time government APIs; Fair Housing–neutral safety copy; plain-English user copy (FR-019); thin client (no wait math in Next.js)

**Scale/Scope**: UX polish across five categories; scoring detail + ScoreBreakdown; no national scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodIQ Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**: Next.js / FastAPI / PostGIS / Redis / workers under existing trees
- [x] **II. Thin Client, Fat API**: Sub-score math and detail assembly in scoring worker + API `score_service`; web only renders (optional `tone_score` for color, no client recomputation of wait)
- [x] **III. Precomputed Data Path**: FEMA/Timely ingest → score job writes `score_detail`; report serves DB/Redis
- [x] **IV. API Contracts & Versioning**: Extend `/api/v1/score/{address_id}` payload additively (`sub_scores`; optional factor `tone_score`); no new version prefix
- [x] **V. Security & Secrets**: No new secrets required for FEMA ArcGIS public layer; CMS Provider Data public; existing DB/Mapbox/EPA/FBI keys unchanged
- [x] **VI. Test Alongside Features**: Formula, API, and web tests planned for polish
- [x] **VII. Observability & Graceful Degradation**: Missing NRI/timely → air-only / access+quality-only with unavailable stats; structured worker logs
- [x] **VIII. Clear User-Facing Errors**: Unavailable hazard/wait copy; `SCORE_UNAVAILABLE` unchanged

**Post-design re-check (2026-07-16 polish)**: Gates still pass. Plain-English labels and tone_score keep business logic server-side.

## Project Structure

### Documentation (this feature)

```text
specs/004-report-subscores/
├── plan.md              # This file
├── research.md          # Phase 0 (+ §10 UX polish)
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── score-api.md
│   └── worker-cli.md
└── tasks.md             # /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
apps/web/src/components/report/ScoreBreakdown.tsx   # category boxes + tone
apps/web/src/types/api.ts                           # optional Factor.tone_score
apps/api/app/schemas/score.py                       # pass-through tone_score if added
apps/api/app/services/score_service.py
workers/scoring/detail.py                           # labels, schools-by-level, wait tone
workers/scoring/compute.py                          # nearest schools per level; ACS employed/labor_force
workers/tests/                                      # polish assertions
```

**Structure Decision**: No new packages; polish stays in existing scoring + report UI files.

## Complexity Tracking

> No constitution violations requiring justification.
