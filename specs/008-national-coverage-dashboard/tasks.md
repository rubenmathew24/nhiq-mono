# Tasks: National Coverage Dashboard

**Input**: Design documents from `/specs/008-national-coverage-dashboard/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup

- [x] T001 Verify `specs/008-national-coverage-dashboard/` artifacts and `.specify/feature.json` point here
- [x] T002 [P] Confirm Commit #2 gates: plan + tasks ready before coding

## Phase 2: Foundational

- [x] T003 Add Pydantic coverage schemas in `apps/api/app/schemas/coverage.py` per `contracts/coverage-api.md`
- [x] T004 Confirm API can read `geo_counties` / ingest tables via existing `AsyncSession` (`apps/api/app/db/session.py`)

## Phase 3: User Story 1 — Overall coverage (P1)

- [x] T005 [P] [US1] Add API tests for empty universe + scoring county denominator in `apps/api/tests/test_coverage_service.py`
- [x] T006 [US1] Implement `compute_national_coverage` in `apps/api/app/services/coverage_service.py` (national sources + overall_pct mean)
- [x] T007 [US1] Add `GET /api/v1/coverage` endpoint in `apps/api/app/api/v1/endpoints/coverage.py` and register in `apps/api/app/api/v1/router.py`

## Phase 4: User Story 2 — By state (source filter) (P1)

- [x] T008 [US2] Ensure response `sources[]` includes all 11 jobs with correct `grain` and national done/total/pct in `coverage_service.py`
- [x] T009 [P] [US2] Extend tests for grains: CMS=`state`, cms_timely=`hospital`, county jobs=`county` in `apps/api/tests/test_coverage_service.py`
- [x] T010 [US2] Add per-state breakdown (`states[]`) with per-source stats scoped to each state’s registry counties in `coverage_service.py`
- [x] T011 [P] [US2] Add by-state assertion test in `apps/api/tests/test_coverage_service.py`
- [x] T011b [US2] Overall ↔ By state parity: EPA by-state uses monitor counties only (`0/0` if none); sum(by-state)==national for every job; By state Overall mean skips `total_count=0`; update 008 spec/data-model/contract/research

## Phase 5: Web page

- [x] T012 [US1] Add TypeScript coverage types in `apps/web/src/types/api.ts`
- [x] T013 [US1] Create public `apps/web/src/app/coverage/page.tsx` with **Overall** + **By state** tabs (By state = source filter including Overall; no auth; do not touch middleware auth for `/dashboard`)
- [x] T014 [P] Add nav link to Coverage from `apps/web/src/components/layout/Header.tsx` or landing nav content
- [x] T013b [US2] UX revise: collapse three tabs to Overall + By state; add Overall option to By state source filter in `CoverageViews.tsx`; sync spec/plan/tasks

## Phase 6: Polish

- [x] T015 Run API pytest for coverage tests; fix failures
- [x] T016 Commit #3 implementation (after Commit #2 at implement start)

## Dependencies

- US1 API before web (T006–T007 before T013)
- US2 extends same service after T006 (sources + states)
- No `/speckit-close` unless user asks

## Summary

MVP: T003–T007 + T012–T013. UI: two tabs (Overall, By state with source filter including Overall).
