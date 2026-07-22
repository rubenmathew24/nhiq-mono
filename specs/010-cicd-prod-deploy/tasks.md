# Tasks: CI/CD Prod Deploy Completeness

**Input**: Design documents from `/specs/010-cicd-prod-deploy/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Spec + Constitution VI — schema/migration tests in `apps/api/tests/`; web lint/vitest via `ci-master`; Deploy smoke is HTTP (no Playwright in v1).

**Organization**: Setup → Foundation (migration runner) → US1 Deploy MVP → US3 master PR gate → US2 app-config → US4 smoke → Polish docs.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallel-safe (different files, no incomplete blockers)
- **[Story]**: US1 / US2 / US3 / US4

## Path Conventions

- Workflows: `.github/workflows/`
- Runner: `scripts/apply-sql-migrations.py`
- Manifest: `infra/deploy/app-env.manifest.json`
- SQL: `infra/sql/`
- API tests: `apps/api/tests/`
- Docs: `docs/azure-setup-and-cicd.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold directories and confirm design inputs

- [ ] T001 Confirm feature docs under `specs/010-cicd-prod-deploy/` (plan.md, research.md, data-model.md, contracts/cicd-deploy.md, quickstart.md)
- [ ] T002 [P] Create `infra/deploy/` directory for `app-env.manifest.json`
- [ ] T003 [P] Ensure `scripts/` is the home for `apply-sql-migrations.py` (create dir if missing)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Migration runner + bookkeeping used by Deploy (US1) and ci-master (US3)

**⚠️ CRITICAL**: No user story Deploy/CI work until the runner works locally

- [ ] T004 Implement `scripts/apply-sql-migrations.py` per `contracts/cicd-deploy.md` (create `schema_migrations`, apply pending `infra/sql/0*.sql` lexically, exclude `init.sql` / `seed_*.sql`, support `sslmode`/`ssl` URLs, non-zero exit on failure, no truncate)
- [ ] T005 [P] Add runner unit/integration tests in `apps/api/tests/test_apply_sql_migrations.py` (apply twice → second no-op; records filenames; fails on bad SQL without wiping data) — skip cleanly if Postgres unavailable when run outside CI
- [ ] T006 Document local runner invocation in `specs/010-cicd-prod-deploy/quickstart.md` if commands drift during implement (keep in sync)

**Checkpoint**: `python scripts/apply-sql-migrations.py --database-url …` succeeds twice against local Postgres

---

## Phase 3: User Story 1 — Promote without manual schema steps (Priority: P1) 🎯 MVP

**Goal**: Change-aware Deploy: detect web/api/schema; migrate before images; skip workers; docs-only no-op

**Independent Test**: Web-only change → only web rebuild; API/SQL change → migrate then API; migrate failure blocks image deploy; workers-only → no worker deploy; docs-only → all skips

### Tests for User Story 1

- [ ] T007 [P] [US1] Extend schema-contract assertions in `apps/api/tests/test_schema_migrations_contract.py` (after runner: required columns e.g. `saved_lookups.is_favorite`, `last_activity_at`, `users.lookups_deduped_at` exist)
- [ ] T008 [P] [US1] Add workflow comment/checklist in `specs/010-cicd-prod-deploy/quickstart.md` §4–5 describing how to validate detect skips / migrate-before-images (manual Actions validation after merge)

### Implementation for User Story 1

- [ ] T009 [US1] Add `detect-changes` job to `.github/workflows/deploy.yml` outputting `web`, `api`, `schema`, `app_config`, `any_app` per `contracts/cicd-deploy.md` / `research.md` (path filters; `force_full` on `workflow_dispatch`; never set workers)
- [ ] T010 [US1] Add `migrate` job in `.github/workflows/deploy.yml` that runs only when `schema==true`, invokes `scripts/apply-sql-migrations.py` against prod DB URL from secrets/Key Vault pattern, fails closed
- [ ] T011 [US1] Gate existing build/push + deploy-api/deploy-web jobs on detect outputs and `needs` migrate success (migrate before API image deploy; skip jobs when flags false; no worker image/job steps)
- [ ] T012 [US1] Ensure docs-only / all-false path: workflow succeeds with clear “nothing to deploy” log and no ACR push / ACA revision / smoke

**Checkpoint**: Deploy MVP — selective images + migrate-before-rollout

---

## Phase 4: User Story 3 — Protect prod via PRs to `master` (Priority: P1)

**Goal**: `ci-master.yml` on PRs to `master` only — web lint/vitest + API pytest with ephemeral PG/Redis + migrations

**Independent Test**: PR → `master` runs checks; ephemeral DB (not Azure); schema drift fails suite; PR → `dev` does not require this workflow

### Tests for User Story 3

- [ ] T013 [P] [US3] Add/extend API integration test covering lookup-store / me-lookups path that depends on migrated columns in `apps/api/tests/test_schema_drift_guard.py` (fails if columns missing)
- [ ] T014 [P] [US3] Confirm existing web Vitest suite remains entrypoint `apps/web` `npm test` / `npm run lint` for CI job

### Implementation for User Story 3

- [ ] T015 [US3] Create `.github/workflows/ci-master.yml` triggered only on `pull_request` branches `[master]` with jobs `api` and `web` named for branch protection (`ci-master / api`, `ci-master / web`)
- [ ] T016 [US3] Wire `api` job: Postgres 16 + Redis service containers, checkout, install API deps, run `scripts/apply-sql-migrations.py`, run `pytest` in `apps/api` (no Azure credentials)
- [ ] T017 [US3] Wire `web` job: Node setup, `npm ci`, `npm run lint`, `npm test` in `apps/web`
- [ ] T018 [US3] Ensure workflow does **not** trigger on PRs to `dev` (branches filter only `master`)

**Checkpoint**: Master promote PRs blocked on red ci-master

---

## Phase 5: User Story 2 — App-needed configuration sync (Priority: P2)

**Goal**: When `infra/deploy/app-env.manifest.json` changes, Deploy syncs Container App env names from existing secrets; otherwise skip; never SKU/firewall

**Independent Test**: Manifest change → app_config job updates ACA settings; unrelated change → skip; no Redis/Postgres SKU steps exist in workflow

### Tests for User Story 2

- [ ] T019 [P] [US2] Add manifest schema validation test or script check in `apps/api/tests/test_app_env_manifest.py` (JSON has `api`/`web` string arrays; no secret values)

### Implementation for User Story 2

- [ ] T020 [US2] Author initial `infra/deploy/app-env.manifest.json` listing required prod env **names** for api/web (from `.env.example` / current ACA usage; names only)
- [ ] T021 [US2] Add `app_config` job in `.github/workflows/deploy.yml` when `app_config==true`: map manifest names → existing GitHub secrets / Key Vault refs; `az containerapp` update; fail if mapping missing; never log secret values
- [ ] T022 [US2] Confirm `.github/workflows/deploy.yml` contains no steps that change Redis/Postgres SKU, firewall, or networking

**Checkpoint**: Config drift on manifest change only

---

## Phase 6: User Story 4 — Post-deploy smoke (Priority: P2)

**Goal**: After any app-facing Deploy update, health + anonymous lookup/score smoke; skip when nothing deployed; failure fails workflow

**Independent Test**: Successful Deploy with api/web → smoke green; docs-only → smoke skipped; forced bad URL → workflow red

### Tests for User Story 4

- [ ] T023 [P] [US4] Add shell/Python smoke helper `scripts/deploy-smoke.sh` or `scripts/deploy_smoke.py` implementing `contracts/cicd-deploy.md` §4 (health, optional web GET, lookup, score) with clear non-zero exit

### Implementation for User Story 4

- [ ] T024 [US4] Add `smoke` job in `.github/workflows/deploy.yml` when `any_app==true` after deploy jobs; use public API/web bases + default address `609 SE Jamaica Dr, Bentonville, AR` (overridable via Actions var `DEPLOY_SMOKE_ADDRESS`)
- [ ] T025 [US4] Skip smoke when all detect flags false; fail Deploy when smoke non-zero

**Checkpoint**: Live prod path verified after real updates

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Operator docs and design-doc honesty

- [ ] T026 [P] Update `docs/azure-setup-and-cicd.md` Deploy section: change detection, migrate-before-images, ci-master, smoke, workers excluded, docs-only no-op
- [ ] T027 [P] Note in `docs/azure-setup-and-cicd.md` (cheat sheet) that design-doc Alembic-after-API in `docs/nhiq-design-main/05-cicd.md` is **not** as-built for this feature
- [ ] T028 Run through `specs/010-cicd-prod-deploy/quickstart.md` validation checklist and fix any drift in scripts/workflows/docs
- [ ] T029 [P] Grep `.github/workflows/deploy.yml` to confirm no `neighborhoodiq-worker` / ACA job start / national-ingest triggers

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Start immediately
- **Foundational (Phase 2)**: After Setup — **blocks** US1–US4
- **US1 (Phase 3)**: After Foundation — MVP Deploy
- **US3 (Phase 4)**: After Foundation (can parallel US1 once runner exists; prefer after T004–T005 green)
- **US2 (Phase 5)**: After US1 detect/job skeleton (needs `app_config` output + deploy.yml structure)
- **US4 (Phase 6)**: After US1 deploy jobs exist (`needs` deploy-api/web)
- **Polish (Phase 7)**: After desired stories complete

### User Story Dependencies

- **US1**: Foundation only
- **US3**: Foundation (migration runner + contract tests); independent of US2/US4
- **US2**: US1 detect + deploy.yml job graph
- **US4**: US1 deploy completion hooks

### Parallel Opportunities

- T002 / T003 in Setup
- T005 with docs T006 after T004
- T007 / T008 after Foundation
- T013 / T014 while drafting ci-master
- T019 while authoring manifest
- T026 / T027 / T029 in Polish

---

## Parallel Example: User Story 1

```text
# After Foundation:
Task: T007 schema contract test in apps/api/tests/test_schema_migrations_contract.py
Task: T008 quickstart validation notes

# Then sequential workflow edits (same file deploy.yml — not parallel):
Task: T009 detect-changes → T010 migrate → T011 gate builds → T012 docs-only path
```

## Parallel Example: User Story 3

```text
Task: T013 schema drift guard test
Task: T014 confirm web lint/test scripts
# Then:
Task: T015–T018 ci-master.yml jobs
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundation (runner)
3. Phase 3 US1 Deploy change detection + migrate-before-images
4. **STOP and VALIDATE** with quickstart §4–5 / a dry workflow_dispatch on a branch if available
5. Then US3 (PR gate) before relying on promotes

### Incremental Delivery

1. Foundation + US1 → prod schema no longer manual for ordinary releases
2. US3 → promote PRs cannot merge blind to schema drift
3. US2 → env manifest sync
4. US4 → post-deploy smoke
5. Polish docs

### Suggested MVP scope

**US1 only** (T001–T012): migration runner + selective Deploy with fail-closed migrate. Ship US3 next in the same feature branch before calling the feature done (both are P1).

---

## Notes

- Do **not** commit/push in `/speckit-tasks`; Commit #2 is `/speckit-implement`
- Never put secret values in `app-env.manifest.json` or workflow logs
- Do not add worker deploy steps “for completeness”
- Prefer `if:` skips over empty no-op jobs that still burn minutes when possible
