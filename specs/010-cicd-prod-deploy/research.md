# Research: 010-cicd-prod-deploy

## 1. Change detection baseline

**Decision**: First Deploy job computes boolean flags (`web`, `api`, `schema`, `app_config`) by diffing `github.event.before`…`github.sha` on `push` to `master`. On `workflow_dispatch`, compare `HEAD` to `HEAD~1` unless input `force_full=true`, which sets all flags true (except workers, always false).

**Path categories**:
| Flag | Paths (any change → true) |
|------|---------------------------|
| `web` | `apps/web/**`, `docker/web.Dockerfile` |
| `api` | `apps/api/**`, `docker/api.Dockerfile` |
| `schema` | `infra/sql/**` **OR** `api` is true (spec FR-004) |
| `app_config` | `infra/deploy/app-env.manifest.json` only |
| workers | never set by Deploy |

Docs-only / workers-only / unrelated → all false → Deploy exits successfully after a “nothing to deploy” summary (no ACR builds, no ACA updates, no smoke against stale “just deployed” assumption — smoke skipped when nothing deployed).

**Rationale**: Matches clarify selective deploy; `dorny/paths-filter` (or equivalent `git diff --name-only`) is standard in GHA. Including API→schema avoids shipping API without attempting pending migrations.

**Alternatives considered**:
- Always rebuild API+web — rejected by clarify Q7
- Compare to last successful Deploy SHA artifact — more accurate across force-pushes but heavier; `before`/`HEAD~1` is enough for linear `master` promotes
- Path-filter schema only when `infra/sql` changes — rejected by clarify Q4 (C)

## 2. Schema migration mechanism (not Alembic-after-API)

**Decision**: Keep as-built **numbered SQL files** under `infra/sql/` (`002_*.sql`…`NNN_*.sql`). Add a small runner (`scripts/apply-sql-migrations.py` or equivalent) that:

1. Ensures table `schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())`.
2. Lists migration files in lexicographic order (exclude `init.sql`, `seed_*.sql`).
3. For each file not in `schema_migrations`, apply inside a transaction when possible, then insert the filename.
4. Idempotent SQL (`IF NOT EXISTS`) remains the authoring style; already-applied Azure files re-run safely once then get recorded.

**Deploy order**: `detect` → (optional `app_config`) → **`migrate` (if schema)** → **build/push only needed images** → **deploy API if needed** → **deploy web if needed** → **smoke if anything app-facing deployed**. Migration failure → fail workflow; build/deploy jobs `needs: migrate` with `if: success()` so new images never roll out after a failed migrate. If schema false, migrate job is skipped and deploy proceeds.

**Rationale**: Spec requires migrate-before-images and fail-closed. Design doc `docs/nhiq-design-main/05-cicd.md` shows Alembic *after* API — that order **violates** this feature’s clarify answers; we deliberately diverge and will note the as-built update in `docs/azure-setup-and-cicd.md`.

**Alternatives considered**:
- Introduce Alembic now — large rewrite of existing SQL history; deferred
- Re-apply all SQL every Deploy without tracking — works with IF NOT EXISTS but obscures “pending” and makes failures noisier
- Migrate after API deploy (design doc) — rejected by clarify Q3 (A)

## 3. App config / secrets wiring

**Decision**: Introduce checked-in **`infra/deploy/app-env.manifest.json`** listing required environment variable **names** (not values) for Container Apps `niq-api` and `niq-web`. Deploy `app_config` job runs only when that file changes: for each name, ensure the Container App has the setting sourced from existing GitHub Actions secrets / Key Vault references already used by the project (no new secret values in git). Missing secret in Actions → fail the job.

**Rationale**: Detectable repo signal per Assumptions; avoids SKU/firewall scope; values stay in Key Vault/Actions.

**Alternatives considered**:
- Diff `.env.example` — noisy, includes local-only keys
- Full Bicep/IaC drift — out of scope (clarify Q6 A)
- No config automation in v1 — would leave FR-008 unmet

## 4. Master PR verification suite

**Decision**: New workflow `.github/workflows/ci-master.yml` on `pull_request` with `branches: [master]` only:

1. **Web**: `npm ci` / lint / `vitest run` when `apps/web` (or shared web paths) changed; if unchanged, skip web job (or run minimal no-op). For safety on promote PRs that often touch many paths, default to **always run both suites** on PRs to `master` (promotes are infrequent; catching cross-package breaks matters more than CI minutes).
2. **API**: install deps, start **service containers** Postgres 16 + Redis, run migration runner against ephemeral DB, `pytest`.
3. **Schema contract test**: pytest (or script) that after migrations, asserts columns required by current API models exist (e.g. `saved_lookups.is_favorite`, `last_activity_at`, `users.lookups_deduped_at`) and exercises lookup-store / me/lookups paths that failed in the 009 incident.

**Rationale**: Clarify Q2 (B) + Q5 (A). Always-on master PR suites beat path-skipping for rare promote PRs.

**Alternatives considered**:
- Live Azure in PR — rejected
- Required on `dev` too — rejected by clarify
- Only path-filtered tests on master PRs — risk missing cross-cuts on promote

## 5. Post-deploy smoke

**Decision**: After successful deploy of API and/or web:

1. `GET {API_PUBLIC_BASE}/health` → expect `status=ok` (always if API deployed; also if only web deployed still hit API health as dependency).
2. If web deployed: `GET {WEB_PUBLIC_BASE}/` → expect HTTP 200.
3. Anonymous lookup: `GET {API}/api/v1/lookup?address={SMOKE_ADDRESS}` → expect 200 + `address_id`; then `GET {API}/api/v1/score/{address_id}` → expect 200 (or accepted “computing” shape if applicable). Default smoke address: `1600 Pennsylvania Avenue NW, Washington, DC`. Override with Actions variable `DEPLOY_SMOKE_ADDRESS` (not a secret).

Smoke runs only when at least one of web/api/schema/app_config actually applied an update; docs-only → skip smoke.

**Rationale**: Clarify Q8/Q9; API-level smoke is more stable than browser E2E in GHA; still proves report path loads.

**Alternatives considered**:
- Playwright against web UI — heavier, flakier for v1
- Signed-in dashboard — rejected by clarify

## 6. Workers

**Decision**: No worker image build, no ACA Job update, no national-ingest trigger in Deploy or ci-master.

**Rationale**: Clarify Q1 (D).

## 7. Documentation

**Decision**: Update `docs/azure-setup-and-cicd.md` Deploy section to describe change detection, migrate-before-images, ci-master, smoke, and explicit worker exclusion. Add a short note in design cheat sheet that Alembic-after-deploy in `05-cicd.md` is **not** as-built for this feature.

**Rationale**: FR-016; keep operator runbooks accurate.

## 8. Agent context script

**Decision**: Skip — repository has no Spec Kit `update-agent-context` script under `.specify/scripts/`.

**Alternatives considered**: Hand-edit AGENTS.md — out of scope unless implement needs it.
