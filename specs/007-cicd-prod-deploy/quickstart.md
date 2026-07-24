# Quickstart: 007-cicd-prod-deploy

Validation guide for operators and implementers. See [contracts/cicd-deploy.md](./contracts/cicd-deploy.md) and [data-model.md](./data-model.md).

## Prerequisites

- Docker (local Postgres/Redis or Compose) — PostGIS preferred for full `init.sql`
- Python 3.12 + `pip install -r scripts/requirements-migrate.txt` (+ `apps/api/requirements.txt` for pytest)
- Node for `apps/web`
- GitHub repo access to Actions (for workflow verification)
- Azure credentials only for Deploy path (not for `ci-master`)

## 1. Migration runner locally

```powershell
cd "C:\Users\ruben\Git Projects\nhiq-mono"
pip install -r scripts/requirements-migrate.txt
# Point at local Compose DB (example)
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/neighborhoodiq"
python scripts/apply-sql-migrations.py --database-url $env:DATABASE_URL
python scripts/apply-sql-migrations.py --database-url $env:DATABASE_URL   # second run: no-op
```

**Expect**: exit 0; `schema_migrations` populated; product tables intact (row counts unchanged).

## 2. Ephemeral integration (CI-shaped)

```powershell
# Prefer PostGIS 16 (matches ci-master). Apply init.sql once, then migrations, then:
cd apps/api
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/neighborhoodiq"
$env:REDIS_URL = "redis://localhost:6379"
$env:SECRET_KEY = "test"
pytest -q
```

**Expect**: suite green including `test_schema_migrations_contract.py` / `test_schema_drift_guard.py`.

## 3. Web unit/lint

```powershell
cd apps/web
npm ci
npm run lint
npm test
```

## 4. Docs-only Deploy no-op (after implement)

1. Open a PR **to `master`** that only changes a markdown file under `docs/` (ci-master still runs).
2. After merge/push to `master`, open the Deploy run: detect job shows `any_app=false`; no ACR push; no ACA revision; smoke skipped; workflow success.

## 5. Schema-before-images (after implement)

1. Change under `infra/sql/` or `apps/api/` on `master`.
2. Deploy: **Apply SQL migrations** runs and succeeds **before** Build/Deploy API when those jobs run.
3. If migrate fails, build/deploy must not roll out new images.

## 6. Smoke (prod Deploy)

```powershell
python scripts/deploy_smoke.py --api-base https://api.nh-iq.com --web-base https://nh-iq.com --address "1600 Pennsylvania Avenue NW, Washington, DC"
```

After a real API/web Deploy: Actions smoke job should pass within ~3 minutes.

## 7. Workers unchanged

Change only `workers/**` on `master`: Deploy detect leaves `any_app=false` (unless other paths also changed); no worker image or ACA Job updates.
