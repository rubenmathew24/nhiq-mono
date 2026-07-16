# Tasks: National Ingest

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
