# Implementation Plan: CI/CD Prod Deploy Completeness

**Branch**: `007-cicd-prod-deploy` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-cicd-prod-deploy/spec.md`

## Summary

Make production releases on `master` **change-aware and schema-safe**: Deploy detects which of web / API / SQL / app-env manifest changed, applies pending numbered SQL migrations **before** rolling new API/web images (fail closed), optionally syncs Container App env names from a checked-in manifest, skips workers and infra SKU/firewall work, and finishes with health + anonymous lookup smoke. Add a **`master`-only** PR workflow that runs web lint/tests and API pytest against ephemeral Postgres/Redis with migrations applied—preventing the 006-class “app expects columns Azure never got” outage.

Technical approach detailed in [research.md](./research.md).

## Technical Context

**Language/Version**: GitHub Actions (YAML); Python 3.12 (migration runner + pytest); TypeScript/Node (web Vitest/eslint); existing FastAPI/Next.js apps unchanged in product behavior except CI coverage

**Primary Dependencies**: GitHub Actions, Azure Container Apps + ACR (existing Deploy secrets), Docker Hub `postgres:16` / Redis service containers for CI, `psycopg` or `asyncpg` for migration runner as chosen at implement

**Storage**: Azure Postgres (`schema_migrations` bookkeeping + existing product schema); Redis unchanged as cache; no new product tables beyond bookkeeping

**Testing**: `apps/api/tests/` (pytest + ephemeral PG/Redis in CI); `apps/web` lint + Vitest; Deploy smoke HTTP checks against prod URLs

**Target Platform**: GitHub Actions runners + Azure Container Apps / Flexible Server (prod Deploy only)

**Project Type**: Monorepo CI/CD + thin infra/scripts (not a new user-facing app surface)

**Performance Goals**: Docs-only Deploy finishes with skips in a few minutes (no image builds); master PR integration suite practical for promote PRs; post-deploy smoke completes within 3 minutes (SC-006)

**Constraints**: No secrets in git; no worker deploy; no Redis/Postgres SKU/firewall changes; migrate-before-images; master-only required PR gate; Constitution V (Key Vault / Actions secrets)

**Scale/Scope**: Two workflows (`deploy.yml` enhanced, new `ci-master.yml`); one migration runner script; one env manifest; docs update; a small set of schema-contract tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodInsight Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**: Stays on GitHub Actions, Azure Container Apps, Postgres, Redis, FastAPI, Next.js; code under `apps/`, `infra/`, `scripts/`, `.github/workflows/` — no alternate cloud/CI product
- [x] **II. Thin Client, Fat API**: No business logic moved to Next.js; smoke uses public API lookup/score
- [x] **III. Precomputed Data Path**: Unchanged; smoke consumes existing lookup/score path
- [x] **IV. API Contracts & Versioning**: No `/api/v1` breaking changes required; CI asserts existing contracts
- [x] **V. Security & Secrets**: Manifest lists names only; Deploy uses Actions/Key Vault; smoke uses public endpoints; no DB exposure beyond existing runner access pattern
- [x] **VI. Test Alongside Features**: Master PR gate + schema contract tests planned; **note**: clarify scopes *required* gate to `master` only (constitution also expects a bar before `dev` merge — developers still run suites locally / existing practice; automated required check on `dev` deferred, not contradicted by shipping reusable jobs)
- [x] **VII. Observability & Graceful Degradation**: Workflow logs must show skip/fail reasons; Deploy failure on migrate/smoke is explicit
- [x] **VIII. Clear User-Facing Errors**: N/A for user UI; operator-facing Actions errors should name migrate vs smoke vs build failure clearly

**Design-doc conflict (intentional)**: `docs/nhiq-design-main/05-cicd.md` shows Alembic **after** API deploy. This plan follows the feature spec (migrate **before** images, numbered SQL runner). Update as-built docs accordingly; do not implement the old design order.

## Project Structure

### Documentation (this feature)

```text
specs/007-cicd-prod-deploy/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cicd-deploy.md
└── tasks.md             # /speckit-tasks (not this command)
```

### Source Code (repository root) — planned touchpoints

```text
.github/workflows/
├── deploy.yml           # detect → migrate → conditional build/deploy → smoke
└── ci-master.yml        # NEW — PR to master only
scripts/
└── apply-sql-migrations.py   # NEW — schema_migrations runner
infra/
├── sql/                 # existing numbered migrations (+ optional 010 bootstrap SQL if needed)
└── deploy/
    └── app-env.manifest.json  # NEW — required env names
apps/api/tests/          # schema contract / migration integration tests
docs/azure-setup-and-cicd.md   # operator docs
```

**Structure Decision**: Extend existing Deploy workflow and add `ci-master.yml`; keep SQL files as source of truth; no Alembic introduction in this feature.

## Complexity Tracking

| Violation / tension | Why Needed | Simpler Alternative Rejected Because |
|---------------------|------------|-------------------------------------|
| Required CI on `master` only (not `dev`) | Explicit clarify Q5 (A) | Constitution-style “same bar everywhere” via required `dev` checks — user deferred; suites remain runnable anytime |
| Diverge from design-doc Alembic-after-API | Spec fail-closed migrate-before-images | Following `05-cicd.md` order recreates 009 outage class |
