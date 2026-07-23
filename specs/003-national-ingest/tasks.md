# Tasks: National Ingest (completed archive)

**Input**: Design documents from `/specs/003-national-ingest/`

**Note**: Historical task lists from the original 003 workstream and absorbed features `005-national-report-detail` and `007-national-ingest-redesign`. All items remain checked; no new unchecked work. Path citations below may still mention former feature directories for provenance.

---

## From 003 (original national ingest)


**Input**: Design documents from `/specs/003-national-ingest/`

## Prior phases (checkpoints + national scope)

- [x] T001–T018 — geo registry, scope, checkpoints, FBI centroids, metro/smoke (completed earlier on this branch)

## Phase 8: Inventory + orchestrator (US5)

- [x] T021 Add `workers/ingest/inventory.py` gap inventory (reuse checkpoints); CLI `python -m ingest.inventory`
- [x] T022 Add `counties_with_urban` checkpoint helper if missing
- [x] T023 Implement `workers/ingest/orchestrate/` (queue builder + Azure ARM job start/poll)
- [x] T024 [P] Unit tests: `workers/tests/test_inventory.py`, `test_orchestrate_queue.py`
- [x] T025 Add `.github/workflows/national-ingest.yml` (`workflow_dispatch` only)
- [x] T026 Document orchestrator in `docs/azure-setup-and-cicd.md` + quickstart
- [x] T027 Create ACA `niq-worker-orchestrate`; rebuild worker image; wire SP secrets
- [x] T028 Push branch; update PR #7 body; **do not merge**

## Phase 9: Force states, mid-run status, ARM retries (US6–US7)

- [x] T029 Extend `spec.md` / `plan.md` / `contracts/worker-env.md` for force, status cadence, ARM retries
- [x] T030 Add `workers/ingest/force.py` (`force_enabled`) and honor in checkpoint-using workers + scoring
- [x] T031 Orchestrator: `ORCH_FORCE_STATES` priority scheduling; always set `INGEST_FORCE` on job patch
- [x] T032 GHA: `force_states` input → `ORCH_FORCE_STATES`
- [x] T033 Add `workers/ingest/status_pulse.py`; emit after each worker (orch) and every N units (fbi/acs/bls/urban)
- [x] T034 ARM retries on PATCH/START (429/500/502/503) in `azure_jobs.py`
- [x] T035 [P] Unit tests: force scheduling, StatusPulse, ARM retry
- [x] T036 Update `docs/azure-setup-and-cicd.md` + quickstart

## Phase 10: Slim LA snapshots + exclusive state lists

- [x] T037 Extend `spec.md` / `plan.md` / `contracts/worker-env.md` for slim log contract + exclusive force/filter
- [x] T038 Slim `persist_and_log` console payload; keep full detail in Postgres
- [x] T039 Make `states_needing_work` exclusive when force and/or state_filter set (no gap padding)
- [x] T040 Update Workbook gallery JSON (default Scope=national; no counties string dependency)
- [x] T041 [P] Unit tests: slim payload size; force-only does not pad
- [x] T042 Docs + quickstart; rebuild worker image after merge

---

## From 005 (national-report-detail)


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

---

## From 007 (national-ingest-redesign)


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
