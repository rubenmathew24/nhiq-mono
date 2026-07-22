# Quickstart: 010-cicd-prod-deploy

Validation guide for operators and implementers. See [contracts/cicd-deploy.md](./contracts/cicd-deploy.md) and [data-model.md](./data-model.md).

## Prerequisites

- Docker (local Postgres/Redis or Compose)
- Python 3.12 + `apps/api` deps
- Node for `apps/web`
- GitHub repo access to Actions (for workflow verification)
- Azure credentials only for Deploy path (not for `ci-master`)

## 1. Migration runner locally

```powershell
cd "C:\Users\ruben\Git Projects\nhiq-mono"
# Point at local Compose DB (example)
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/neighborhoodiq"
python scripts/apply-sql-migrations.py --database-url $env:DATABASE_URL
python scripts/apply-sql-migrations.py --database-url $env:DATABASE_URL   # second run: no-op
```

**Expect**: exit 0; `schema_migrations` populated; product tables intact (row counts unchanged).

## 2. Ephemeral integration (CI-shaped)

```powershell
# Start Postgres 16 + Redis (Compose services or docker run)
# Apply migrations, then:
cd apps/api
pytest -q
```

**Expect**: suite green including tests that require `009` columns / lookup list behavior.

## 3. Web unit/lint

```powershell
cd apps/web
npm ci
npm run lint
npm test
```

## 4. Docs-only Deploy no-op (after implement)

1. Open a PR **to `master`** that only changes a markdown file under `docs/` (or push to a test fork).
2. Confirm `ci-master` still runs (gate is on PR target, not path).
3. After merge/push to `master`, open the Deploy run: detect job shows all flags false; no ACR push; no ACA revision; smoke skipped; workflow success.

## 5. Schema-before-images (after implement)

1. Add a harmless idempotent SQL file + an API test that depends on it (or use a staging branch).
2. On Deploy: migrate job runs and succeeds **before** API image deploy steps.
3. Simulate migrate failure (bad SQL on a throwaway branch against non-prod DB only — **never** break prod on purpose without a rollback plan): confirm build/deploy jobs do not roll out new images.

## 6. Smoke (prod Deploy)

After a real API/web Deploy: Actions log shows `/health`, anonymous lookup for Bentonville smoke address, and score fetch succeeding within ~3 minutes.

## 7. Workers unchanged

Change only `workers/**` on `master`: Deploy does not build `neighborhoodiq-worker` or start ACA Jobs.
