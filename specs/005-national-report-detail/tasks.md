# Tasks: National Report Detail Ingest

**Input**: Design documents from `/specs/005-national-report-detail/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Per Constitution Principle VI and plan.md — pytest under `workers/tests/` for inventory priority, ACS population checkpoint, and national scope on FEMA/CMS Timely. Azure smoke remains a manual ops checklist (quickstart).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Workers**: `workers/ingest/`, `workers/scoring/`, `workers/tests/`
- **Docs / infra**: `docs/`, `infra/sql/`, `specs/003-national-ingest/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm repo assets and baseline for 005 work

- [x] T001 Verify `infra/sql/007_report_detail.sql` exists and matches plan (score_detail + fema_nri_tracts + hospital_timely_measures); note any gaps vs `infra/sql/init.sql` mirror
- [x] T002 [P] Confirm Compose already defines `worker-fema` / `worker-cms-timely` in `docker-compose.yml` (no duplicate services); list ACA job names to add in docs (`niq-worker-fema`, `niq-worker-cms-timely`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Scope + checkpoint primitives every story’s national/smoke path needs

**⚠️ CRITICAL**: No user story implementation that depends on national FEMA/Timely or gap inventory should start until this phase is complete

- [x] T003 Replace `assert_dev_scope()` with national-capable scope (smoke | metro_10 | national + `INGEST_STATE_BATCH` when national) in `workers/ingest/fema/run.py`
- [x] T004 [P] Replace `assert_dev_scope()` with national-capable scope (same pattern as other national workers) in `workers/ingest/cms_timely/run.py`
- [x] T005 Tighten `counties_with_acs` in `workers/ingest/checkpoints.py` so a county is done only when tract ACS rows exist **and** `total_population IS NOT NULL` (per `data-model.md` / research §4)
- [x] T006 [P] Add county-level FEMA done helper (e.g. `counties_with_fema_nri`) in `workers/ingest/checkpoints.py` using tract coverage vs `fema_nri_tracts`
- [x] T007 [P] Add state-level CMS Timely done helper (e.g. `states_with_timely_measures`) in `workers/ingest/checkpoints.py` for hospitals in-scope vs `hospital_timely_measures` + active vintage
- [x] T008 [P] Add / extend scoring done helper so counties need fbi_cde safety **and** non-empty `score_detail` for active vintage in `workers/ingest/checkpoints.py` (align with `workers/scoring/compute.py` empty-detail re-score)
- [x] T009 Update `workers/tests/test_scope_refuse_national.py` (or replace) so FEMA/CMS Timely national-with-batch is allowed and national-without-batch still fails clearly

**Checkpoint**: Foundation ready — US1 docs and US3 inventory can proceed

---

## Phase 3: User Story 1 - Operator prepares production schema (Priority: P1) 🎯 MVP

**Goal**: Document idempotent Azure apply of report-detail schema so prod storage is ready without wiping data

**Independent Test**: An operator following only `docs/azure-setup-and-cicd.md` can apply `007` and confirm `score_detail` / FEMA / timely / `total_population` exist without truncating existing scores

### Tests for User Story 1

> Docs/chore story — no runtime test required beyond T001 verification

### Implementation for User Story 1

- [x] T010 [US1] Document `infra/sql/007_report_detail.sql` (and `total_population` confirm) in the Azure schema apply list in `docs/azure-setup-and-cicd.md` (§16 Schema on Azure)
- [x] T011 [P] [US1] Add brief operator note at top of `infra/sql/007_report_detail.sql` pointing to azure-setup apply-on-existing-volume pattern (idempotent, no truncate)
- [x] T012 [US1] Cross-link schema step from `specs/005-national-report-detail/contracts/azure-ops.md` §2 to the azure-setup section (keep contract accurate)

**Checkpoint**: US1 complete — prod schema runbook is discoverable

---

## Phase 4: User Story 2 - Azure smoke gate (Priority: P1)

**Goal**: Document and support Azure/prod smoke (`INGEST_SCOPE=smoke`) after promote so Bentonville expand matches local/dev before National Ingest

**Independent Test**: Following `specs/005-national-report-detail/quickstart.md` V2–V3 (and azure-ops smoke section), operator knows exact job order and pass/fail gate; workers accept smoke scope (T003–T004)

### Tests for User Story 2

- [x] T013 [P] [US2] Add/adjust pytest that smoke/metro scopes still work for FEMA and CMS Timely entrypoints in `workers/tests/test_scope_national_fema_timely.py` (or extend T009 module)

### Implementation for User Story 2

- [x] T014 [US2] Expand smoke gate section in `docs/azure-setup-and-cicd.md` (promote `005→dev→master`, worker image, `INGEST_SCOPE=smoke`, job order acs→fema→cms_timely→scoring, Bentonville UI check, **do not** start National Ingest on fail)
- [x] T015 [P] [US2] Align `specs/005-national-report-detail/quickstart.md` V1–V3 with the azure-setup smoke section (same commands / expectations)
- [x] T016 [P] [US2] Ensure `specs/005-national-report-detail/contracts/azure-ops.md` §1 and §4 match the documented promote + smoke gate

**Checkpoint**: US2 complete — Azure smoke gate is an explicit ops checklist

---

## Phase 5: User Story 3 - National gap-fill without force (Priority: P1)

**Goal**: Inventory + orchestrator treat report-detail as gaps, prefer base-complete states, run only missing stages (fema / cms_timely / acs-pop / score_detail) without `force_states`

**Independent Test**: Unit tests with fixture inventory: five base-complete detail-gapped states + virgin states → `max_states=3` picks from class A first; workers_needed returns only detail stages; ACS pop-null counties remain ACS gaps

### Tests for User Story 3 (REQUIRED — Principle VI)

- [x] T017 [P] [US3] Unit tests for ACS population done-check in `workers/tests/test_acs_population_checkpoint.py`
- [x] T018 [P] [US3] Unit tests for `states_needing_work` class A-before-B priority and `workers_needed_for_state` detail-only stages in `workers/tests/test_inventory_report_detail.py`
- [x] T019 [P] [US3] Unit tests for FEMA county / CMS Timely state / scoring score_detail checkpoint helpers in `workers/tests/test_report_detail_checkpoints.py`

### Implementation for User Story 3

- [x] T020 [US3] Extend `PIPELINE_WORKERS` and `WORKER_ACA_JOB` with `fema` → `niq-worker-fema` and `cms_timely` → `niq-worker-cms-timely` (order: … bls → fema → cms_timely → scoring) in `workers/ingest/inventory.py`
- [x] T021 [US3] Wire `build_inventory` gaps for `fema`, `cms_timely`, tightened `acs`, and score_detail-aware `scoring` using checkpoint helpers in `workers/ingest/inventory.py`
- [x] T022 [US3] Implement class A / class B ordering in `states_needing_work` in `workers/ingest/inventory.py` per research §5 and `contracts/national-orchestrator.md` (preserve force/exclusive behavior)
- [x] T023 [US3] Verify orchestrator starts new ACA job names via inventory map in `workers/ingest/orchestrate/run.py` (fix imports/maps if hard-coded)
- [x] T024 [US3] Extend `JOB_NAMES` and completion % for `fema` and `cms_timely` (and score_detail-aware scoring if needed) in `workers/ingest/status.py`
- [x] T025 [P] [US3] Confirm `workers/ingest/acs/run.py` uses updated `counties_with_acs` (no separate force path required for pop backfill)
- [x] T026 [US3] Update `specs/003-national-ingest/quickstart.md` pipeline order to include fema → cms_timely before scoring and note report-detail gap-fill without force

**Checkpoint**: US3 complete — national path can backfill report-detail on previously gathered states without force

---

## Phase 6: User Story 4 - Production docs & job list (Priority: P2)

**Goal**: Full operator runbook: ACA job creation, status visibility, merge/promote → schema → smoke → national

**Independent Test**: Second reader can create/start `niq-worker-fema` / `niq-worker-cms-timely` and find status guidance using only `docs/azure-setup-and-cicd.md` + contracts

### Tests for User Story 4

> Docs story — validate by checklist walkthrough against quickstart (no new automated tests)

### Implementation for User Story 4

- [x] T027 [US4] Add `niq-worker-fema` and `niq-worker-cms-timely` to the manual ACA job list and run-order diagram in `docs/azure-setup-and-cicd.md` §16
- [x] T028 [P] [US4] Document how to create the two ACA jobs (image, command, secrets, timeout) in `docs/azure-setup-and-cicd.md` (or linked subsection)
- [x] T029 [P] [US4] Document status/Workbook expectations for new jobs in `docs/azure-setup-and-cicd.md` (re-run `niq-worker-status`; dynamic jobs table)
- [x] T030 [US4] Sync `specs/005-national-report-detail/contracts/azure-ops.md` §3–§6 with final azure-setup wording
- [x] T031 [P] [US4] Add failure-signal / no-force note to National ingest section in `docs/azure-setup-and-cicd.md` pointing at report-detail backfill behavior

**Checkpoint**: US4 complete — ops docs match contracts

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Consistency and quickstart dry-run readiness

- [x] T032 [P] Run `workers` pytest modules added/updated for 005 (`test_acs_population_checkpoint.py`, `test_inventory_report_detail.py`, `test_report_detail_checkpoints.py`, scope tests) and fix regressions
- [x] T033 [P] Re-read `specs/005-national-report-detail/quickstart.md` against implemented inventory/docs; fix command/name drift
- [x] T034 Confirm `.github/workflows/national-ingest.yml` needs no input changes (orchestrator discovers jobs via code); add a one-line comment in workflow or azure-setup if helpful
- [x] T035 Mark any deferred CMS Timely fetch-skip optimization as out of scope in `specs/005-national-report-detail/research.md` Notes if still deferred after implement

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Start immediately
- **Foundational (Phase 2)**: After Setup — **BLOCKS** US2 runtime assumptions and US3
- **US1 (Phase 3)**: Can start after Setup (docs); prefer after T001
- **US2 (Phase 4)**: After Foundational (scope lift) + ideally US1 schema docs
- **US3 (Phase 5)**: After Foundational (checkpoints + scope)
- **US4 (Phase 6)**: After US2/US3 so docs match real job names and behavior
- **Polish (Phase 7)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: Schema docs — independent MVP
- **US2 (P1)**: Depends on Foundational scope lift; docs depend on US1 schema note
- **US3 (P1)**: Depends on Foundational checkpoints; delivers core national behavior
- **US4 (P2)**: Depends on US3 job names + US2 smoke narrative for a coherent runbook

### Parallel Opportunities

- T003 ∥ T004 (scope lift on two workers)
- T006 ∥ T007 ∥ T008 (checkpoint helpers)
- T017 ∥ T018 ∥ T019 (US3 tests)
- T014–T016 (US2 doc surfaces)
- T027–T029 / T031 (US4 doc slices)

---

## Parallel Example: User Story 3

```text
# Tests in parallel:
Task: T017 workers/tests/test_acs_population_checkpoint.py
Task: T018 workers/tests/test_inventory_report_detail.py
Task: T019 workers/tests/test_report_detail_checkpoints.py

# Then implement inventory + status (sequential on inventory.py):
Task: T020–T022 workers/ingest/inventory.py
Task: T023 workers/ingest/orchestrate/run.py
Task: T024 workers/ingest/status.py
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 + T010–T012 — Azure schema apply is documented  
2. Validate: operator can apply `007` from docs alone  

### Incremental Delivery

1. Foundational (T003–T009) — national FEMA/Timely + checkpoints  
2. US3 — inventory priority + status (unlocks no-force national backfill)  
3. US2 + US4 — smoke gate + full ACA/job docs  
4. Polish — pytest green + quickstart sync  

### Suggested MVP scope

**US1 only** for a docs-only promoteable slice; **US1 + Foundational + US3** is the minimum runtime MVP that satisfies the clarify “no force / prefer base-complete states” requirement before Azure smoke/national.

---

## Notes

- [P] = different files, no incomplete dependencies
- Do **not** commit in `/speckit-tasks` — Commit #2 (plan + tasks) happens at start of `/speckit-implement`
- Force must never be the only path to report-detail on previously gathered states
- ACA job **creation** in Azure is an operator step documented in US4 (code ships job names + modules)
