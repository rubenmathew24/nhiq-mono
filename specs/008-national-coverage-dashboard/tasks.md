# Tasks: National Coverage Dashboard

**Input**: Design documents from `/specs/008-national-coverage-dashboard/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup

- [ ] T001 Verify `specs/008-national-coverage-dashboard/` artifacts and `.specify/feature.json` point here
- [ ] T002 [P] Confirm Commit #2 gates: plan + tasks ready before coding

## Phase 2: Foundational

- [ ] T003 Add Pydantic coverage schemas in `apps/api/app/schemas/coverage.py` per `contracts/coverage-api.md`
- [ ] T004 Confirm API can read `geo_counties` / ingest tables via existing `AsyncSession` (`apps/api/app/db/session.py`)

## Phase 3: User Story 1 — Overall coverage (P1)

- [ ] T005 [P] [US1] Add API tests for empty universe + scoring county denominator in `apps/api/tests/test_coverage_service.py`
- [ ] T006 [US1] Implement `compute_national_coverage` in `apps/api/app/services/coverage_service.py` (national sources + overall_pct mean)
- [ ] T007 [US1] Add `GET /api/v1/coverage` endpoint in `apps/api/app/api/v1/endpoints/coverage.py` and register in `apps/api/app/api/v1/router.py`

## Phase 4: User Story 2 — By source (P1)

- [ ] T008 [US2] Ensure response `sources[]` includes all 11 jobs with correct `grain` and national done/total/pct in `coverage_service.py`
- [ ] T009 [P] [US2] Extend tests asserting CMS/Timely use state grain and county jobs use county grain in `apps/api/tests/test_coverage_service.py`

## Phase 5: User Story 3 — By state (P1)

- [ ] T010 [US3] Add per-state breakdown (`states[]`) with per-source stats scoped to each state’s registry counties in `coverage_service.py`
- [ ] T011 [P] [US3] Add by-state assertion test in `apps/api/tests/test_coverage_service.py`

## Phase 6: Web page

- [ ] T012 [US1] Add TypeScript coverage types in `apps/web/src/types/api.ts`
- [ ] T013 [US1] Create public `apps/web/src/app/coverage/page.tsx` with overall / by source / by state views (no auth; do not touch middleware auth for `/dashboard`)
- [ ] T014 [P] Add nav link to Coverage from `apps/web/src/components/layout/Header.tsx` or landing nav content

## Phase 7: Polish

- [ ] T015 Run API pytest for coverage tests; fix failures
- [ ] T016 Commit #3 implementation (after Commit #2 at implement start)

## Dependencies

- US1 API before web (T006–T007 before T013)
- US2/US3 extend same service after T006
- No `/speckit-close` unless user asks

## Summary

29→16 tasks for this feature. MVP: T003–T007 + T012–T013.
