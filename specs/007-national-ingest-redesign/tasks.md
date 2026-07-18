# Tasks: National Ingest Redesign

**Input**: Design documents from `/specs/007-national-ingest-redesign/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Per Constitution Principle VI — include pytest tasks under `workers/tests/` for each story that changes runtime behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Workers**: `workers/ingest/<source>/`, `workers/scoring/`
- **Orchestration**: `workers/ingest/orchestrate/`, `workers/ingest/inventory.py`
- **CI / scripts**: `.github/workflows/national-ingest.yml`, `scripts/national-ingest.ps1`
- **Docs**: `docs/azure-setup-and-cicd.md`
- **Tests**: `workers/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm feature workspace and design artifacts are ready for implementation

- [x] T001 Verify branch `007-national-ingest-redesign` and that `specs/007-national-ingest-redesign/{plan,research,data-model,quickstart}.md` plus `contracts/` exist
- [x] T002 [P] Confirm Commit #2 prerequisites: plan + tasks ready to commit at start of `/speckit-implement` (no code yet)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared env/contracts awareness; no schema migrations needed

**⚠️ CRITICAL**: Status denominator (US1) and worker fetch rewrites (US3) can proceed after this; continuous orchestration (US2) depends on exit-code contract documented here

- [x] T003 Document/implement shared env defaults used by orchestrator and workers per `specs/007-national-ingest-redesign/contracts/worker-env.md` (reference constants or parse helpers as needed in `workers/ingest/`)
- [x] T004 Confirm inventory / `parse_state_batch` already accepts multi-state `INGEST_STATE_BATCH` in `workers/ingest/inventory.py` and workers’ `active_county_fips()` (no change if already true; note any gap)

**Checkpoint**: Foundation ready — US1–US3 can proceed in parallel where marked [P]

---

## Phase 3: User Story 1 - Accurate national progress (Priority: P1) 🎯 MVP

**Goal**: Scoring (and all jobs) use the full 50+DC county universe as denominator; scoring done counted at county grain

**Independent Test**: With only a subset of states scored, national status shows scoring % ≈ completed counties ÷ national county count (~3143), not tracts÷loaded tracts

### Tests for User Story 1

- [x] T005 [P] [US1] Add scoring-denominator regression test in `workers/tests/test_status_scoring_denominator.py` (or extend existing status tests) covering incomplete census vs full `geo_counties`

### Implementation for User Story 1

- [x] T006 [US1] Fix scoring progress denominator in `workers/ingest/status.py` to use national `geo_counties` count and county-grain done (every tract has fbi_cde + non-empty `score_detail`)

**Checkpoint**: Status snapshot scoring % is trustworthy for partial nations

---

## Phase 4: User Story 3 - Faster collection (Priority: P1)

**Goal**: Bulk/wide fetch for FEMA/ACS/Urban; FBI cache+concurrency; secondary EPA/BLS bulk + CMS Timely skip-done

**Independent Test**: Represent multi-state batch finishes with far fewer upstream calls; required table shapes unchanged for scoring

### Tests for User Story 3

- [x] T007 [P] [US3] Add FEMA bulk CSV parse/upsert unit test in `workers/tests/test_fema_bulk.py`
- [x] T008 [P] [US3] Add ACS per-state `county:*` fetch unit test in `workers/tests/test_acs_state_fetch.py`
- [x] T009 [P] [US3] Add Urban per-state fips fetch + skip-done unit test in `workers/tests/test_urban_state_fetch.py`
- [x] T010 [P] [US3] Add FBI agency-list cache unit test in `workers/tests/test_fbi_agency_cache.py`
- [x] T011 [P] [US3] Add CMS Timely skip-done unit test in `workers/tests/test_cms_timely_skip.py`

### Implementation for User Story 3

- [x] T012 [P] [US3] Rewrite FEMA to national NRI tracts CSV zip bulk download/parse/upsert in `workers/ingest/fema/client.py` and `workers/ingest/fema/run.py` (remove per-county ArcGIS + N+1 checkpoint)
- [x] T013 [P] [US3] Change ACS to `fetch_state_tract_rows` with `in=state:{SS} county:*` and pending-state loop in `workers/ingest/acs/client.py` and `workers/ingest/acs/run.py`
- [x] T014 [P] [US3] Add Urban `fetch_directory_for_states` via `?fips=` + skip-done in `workers/ingest/urban/client.py` and `workers/ingest/urban/run.py`
- [x] T015 [P] [US3] Cache FBI `fetch_agencies_by_state`, shared rate limiter, and `ThreadPoolExecutor` county concurrency in `workers/ingest/fbi/client.py` and `workers/ingest/fbi/run.py`
- [x] T016 [P] [US3] Add EPA bulk AirData file path with `EPA_USE_BULK_FILES` fallback in `workers/ingest/epa/client.py` and `workers/ingest/epa/run.py`
- [x] T017 [P] [US3] Add BLS LAUS bulk flat-file path with `BLS_USE_BULK_FILES` fallback in `workers/ingest/bls/client.py` and `workers/ingest/bls/run.py`
- [x] T018 [P] [US3] Add CMS Timely skip-done for active `data_vintage` in `workers/ingest/cms_timely/run.py`

**Checkpoint**: Primary bottleneck sources use bulk/wide/concurrent paths; secondary flags default on

---

## Phase 5: User Story 2 - Continuous nationwide completion (Priority: P1)

**Goal**: Continuous orchestrator batches states, exits 0/2/1; GHA chains; PowerShell one-command loop; raised ACA timeouts

**Independent Test**: Continuous run across more states than one batch; cycles continue; eventually `orch_cycle_result=complete` or auto-handoff on budget

### Tests for User Story 2

- [x] T019 [P] [US2] Add orchestrator batching + exit-code unit tests in `workers/tests/test_orchestrate_continuous.py` (or extend `test_inventory.py` / `test_force_status_arm.py`)

### Implementation for User Story 2

- [x] T020 [US2] Implement `ORCH_CONTINUOUS`, `ORCH_BATCH_STATES`, `ORCH_TIME_BUDGET_SECONDS`, multi-state one-execution batching, and exit codes 0/2/1 with log markers in `workers/ingest/orchestrate/run.py` and `workers/ingest/orchestrate/azure_jobs.py`
- [x] T021 [US2] Update `.github/workflows/national-ingest.yml`: `continuous` input (default true), `timeout-minutes: 350`, chain executions on `more_work`, self-redispatch with `chain_depth` (max 50), `actions: write`, extend interesting-log regex for `orch_cycle_result` / `national_progress`
- [x] T022 [US2] Create `scripts/national-ingest.ps1` continuous loop (exit 2→retry, 0/1 stop) with optional `-AllowMyIp` firewall helper
- [x] T023 [US2] Apply ACA `--replica-timeout` updates: orchestrator `21600`, per-source/scoring jobs `10800` via `az containerapp job update` (document commands if env unavailable in CI)

**Checkpoint**: One Action or one PowerShell command can drive the nation to completion with chaining

---

## Phase 6: User Story 4 - Resumability (Priority: P2)

**Goal**: Skip-done / checkpoints remain durable; continuous restart resumes gaps only

**Independent Test**: Partially complete a source, interrupt, restart continuous; finished units skipped

### Implementation for User Story 4

- [x] T024 [US4] Verify FEMA/ACS/Urban/FBI/CMS Timely skip-done and orchestrator inventory selection resume from gaps only; fix any wipe or force-all regressions in affected `workers/ingest/**/run.py` and `workers/ingest/orchestrate/run.py`
- [x] T025 [P] [US4] Add or extend a resume/skip regression assertion in `workers/tests/` covering at least one primary source + continuous inventory selection

**Checkpoint**: Interrupt + restart does not re-fetch completed units

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Docs, image ship, Commit #3

- [x] T026 Update National ingest section in `docs/azure-setup-and-cicd.md` (bulk strategy, continuous env, timeouts, exit codes, PowerShell, scoring denominator note)
- [x] T027 Run pytest for new/changed tests under `workers/tests/` and fix failures
- [x] T028 Rebuild and push worker image `neighborhoodiqacr.azurecr.io/neighborhoodiq-worker:dev` so ACA runs new code
- [x] T029 Commit #3 implementation on `007-national-ingest-redesign` (after Commit #2 plan+tasks at implement start)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — blocks story work only if env/batch confirmation finds gaps
- **US1 (Phase 3)**: After Foundational — MVP accuracy fix; no dependency on US3 bulk rewrites
- **US3 (Phase 4)**: After Foundational — parallel with US1; independent of US2
- **US2 (Phase 5)**: After Foundational; benefits from US3 but can land orchestrator/GHA/script in parallel with worker rewrites
- **US4 (Phase 6)**: After US2 + US3 skip-done paths exist
- **Polish (Phase 7)**: After all stories complete

### User Story Dependencies

- **US1 (P1)**: Independent — status.py only
- **US3 (P1)**: Independent worker files — [P] across FEMA/ACS/Urban/FBI/EPA/BLS/CMS
- **US2 (P1)**: Independent of US1; uses multi-state batch already supported by workers
- **US4 (P2)**: Depends on US2 continuous + US3 skip-done implementations

### Parallel Opportunities

- T005–T011 test stubs in parallel
- T012–T018 worker rewrites in parallel (different directories)
- T021–T022 GHA + PowerShell in parallel after T020 contract is clear
- T026 docs can draft while T027 tests run

### Parallel Example: User Story 3

```text
# Parallel worker rewrites:
T012 FEMA bulk | T013 ACS state | T014 Urban state | T015 FBI concurrency
T016 EPA bulk  | T017 BLS bulk  | T018 CMS Timely skip
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1–2
2. Deliver T005–T006 (scoring denominator)
3. **STOP and VALIDATE**: status % trustworthy on partial nation
4. Continue US3 + US2 for finishable nationwide runs

### Incremental Delivery

1. US1 → accurate progress
2. US3 primary (FEMA/ACS/Urban/FBI) → major wall-clock win
3. US2 → hands-off continuous completion
4. US3 secondary (EPA/BLS) + US4 resume hardening
5. Polish: docs, image, ACA timeouts, Commit #3

### Notes

- Commit #2 (plan + tasks) happens at the **start** of `/speckit-implement`, before coding
- Commit #3 after all implementation tasks including image/timeouts where environment allows
- `/speckit-close` pushes branch and opens PR into **`dev`** (not `master`)

---

## Task Summary

| Phase | Story | Task IDs | Count |
|-------|-------|----------|-------|
| Setup | — | T001–T002 | 2 |
| Foundational | — | T003–T004 | 2 |
| US1 | Accurate progress | T005–T006 | 2 |
| US3 | Faster collection | T007–T018 | 12 |
| US2 | Continuous completion | T019–T023 | 5 |
| US4 | Resumability | T024–T025 | 2 |
| Polish | — | T026–T029 | 4 |
| **Total** | | | **29** |

**Suggested MVP**: T001–T006 (accurate scoring %). Full feature needs through T029.

---

## Phase 8: Convergence

- [x] T030 CRITICAL: Fail closed when national `geo_counties` universe is empty in `workers/ingest/status.py`, `workers/ingest/inventory.py`, and `workers/ingest/orchestrate/run.py` — clear error log + non-zero exit; never emit `orch_cycle_result=complete` or treat empty registry as success per Edge Cases / Assumptions / FR-014 (`missing`)
- [x] T031 Fail closed (or refuse national continuous/status success) when `geo_counties` is incomplete for included 50+DC jurisdictions (e.g. distinct included `state_fips` ≠ 51) in `workers/ingest/geo/scope.py` and callers per Edge Cases / FR-001 / SC-001 (`partial`)
- [x] T032 Distinguish “nothing left to schedule” vs “nation inventory clear” in `workers/ingest/orchestrate/run.py`: when remaining gaps exist only on `exclude_states`, do not emit `orch_cycle_result=complete` (use non-complete stop + clear log) per Edge Cases / FR-014 (`contradicts`)
- [x] T033 [P] Add regression tests in `workers/tests/` for empty registry fail-closed, incomplete registry fail-closed, and exclude-only remaining gaps ≠ complete per Constitution VI / T030–T032 (`missing`)
