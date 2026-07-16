# Tasks: National Ingest

**Input**: Design documents from `/specs/003-national-ingest/`

## Prior phases (checkpoints + national scope)

- [x] T001–T018 — geo registry, scope, checkpoints, FBI centroids, metro/smoke (completed earlier on this branch)

## Phase 8: Inventory + orchestrator (US5)

- [ ] T021 Add `workers/ingest/inventory.py` gap inventory (reuse checkpoints); CLI `python -m ingest.inventory`
- [ ] T022 Add `counties_with_urban` checkpoint helper if missing
- [ ] T023 Implement `workers/ingest/orchestrate/` (queue builder + Azure ARM job start/poll)
- [ ] T024 [P] Unit tests: `workers/tests/test_inventory.py`, `test_orchestrate_queue.py`
- [ ] T025 Add `.github/workflows/national-ingest.yml` (`workflow_dispatch` only)
- [ ] T026 Document orchestrator in `docs/azure-setup-and-cicd.md` + quickstart
- [ ] T027 Create ACA `niq-worker-orchestrate`; rebuild worker image; wire SP secrets
- [ ] T028 Push branch; update PR #7 body; **do not merge**
