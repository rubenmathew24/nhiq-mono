# Tasks: National Ingest

**Input**: Design documents from `/specs/003-national-ingest/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup

- [x] T001 Add `infra/sql/006_geo_counties.sql` per data-model.md
- [x] T002 [P] Document `INGEST_SCOPE` / `INGEST_STATE_BATCH` / `INGEST_GEO_LOAD_ALL` in `.env.example`

## Phase 2: Foundational

- [x] T003 Create `workers/ingest/geo/jurisdictions.py` with 50+DC included FIPS and documented empty/extension territory list + state abbr map
- [x] T004 Create `workers/ingest/geo/scope.py` resolving smoke / metro_10 / national counties; reject national without batch
- [x] T005 Create `workers/ingest/checkpoints.py` with per-worker “county done?” SQL helpers and skip logging
- [x] T006 Implement `workers/ingest/geo/run.py` (`python -m ingest.geo.run`) TIGER county load + upsert + skip-done
- [x] T007 [P] Unit tests: `workers/tests/test_national_scope.py` (batch required, invalid state, smoke/metro unchanged)

**Checkpoint**: Scope + registry loadable

## Phase 3: User Story 1 — State batch end-to-end (P1)

- [x] T008 [US1] Wire census/epa/nces/acs/bls/cms/scoring to `geo.scope` active counties/states for national
- [x] T009 [US1] Wire status.py national denominator from `geo_counties` (remove stub)
- [x] T010 [US1] Add Compose service `worker-geo` + docs §16 national runbook in `docs/azure-setup-and-cicd.md`
- [x] T011 [US1] Test status national denominator helper in `workers/tests/test_ingest_status.py`

## Phase 4: User Story 2 — Checkpoints (P1)

- [x] T012 [US2] Census/EPA/NCES/ACS/BLS: skip counties (or states) already done before fetch; log skip_checkpoint
- [x] T013 [US2] CMS: skip states already having hospitals; FBI already checkpoints — add skip if agencies exist
- [x] T014 [US2] Scoring: skip counties whose tracts already have fbi_cde safety (or document tract loop skip)
- [x] T015 [US2] Tests for checkpoint skip helpers in `workers/tests/test_checkpoints.py`

## Phase 5: User Story 3 — FBI centroids (P2)

- [x] T016 [US3] FBI uses `geo_counties` centroid + name when national (fallback fixture addresses for metro)
- [x] T017 [US3] Test point resolution helper

## Phase 6: User Story 4 — Preserve metro/smoke (P2)

- [x] T018 [US4] Ensure fixture paths unchanged when scope metro_10/smoke; regression tests in test_national_scope / test_county_allowlist

## Phase 7: Polish

- [ ] T019 Apply 006 on Azure Postgres; create/update `niq-worker-geo` ACA job; rebuild worker image
- [ ] T020 Open PR into `dev`; document first state-batch ops steps in PR body

## Dependencies

- T003–T007 before T008+
- T012–T014 after T008
- T016 after geo table + scope
- T019–T020 after code complete
