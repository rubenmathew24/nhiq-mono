# Contracts: CI/CD Deploy & Master PR Gate

## 1. Deploy workflow outputs (`detect-changes` job)

Other jobs consume these outputs (string `"true"` / `"false"`):

| Output | When true |
|--------|-----------|
| `web` | Web-relevant paths changed (or `force_full`) |
| `api` | API-relevant paths changed (or `force_full`) |
| `schema` | `infra/sql/**` changed **or** `api` true (or `force_full`) |
| `app_config` | `infra/deploy/app-env.manifest.json` changed (or `force_full`) |
| `any_app` | any of web/api/schema/app_config |

## 2. Migration runner CLI

```text
python scripts/apply-sql-migrations.py --database-url "$DATABASE_URL"
```

| Exit code | Meaning |
|-----------|---------|
| 0 | All pending migrations applied (or none pending) |
| ≠0 | Apply failed; Deploy must not continue to image rollout |

**Side effect**: Ensures `schema_migrations` and applies pending `infra/sql/0*.sql` (exclude init/seed).

**SSL**: Support URLs with `sslmode=require` / `ssl=require` as used by Azure vs local.

## 3. Master PR workflow

**Trigger**: `pull_request` → `master` only.

**Required observable checks** (names for branch protection):

| Check | Responsibility |
|-------|----------------|
| `ci-master / api` | Migrations on ephemeral Postgres + Redis + pytest |
| `ci-master / web` | lint + vitest |

## 4. Post-deploy smoke HTTP contract

| Step | Request | Success |
|------|---------|---------|
| Health | `GET {API}/health` | 200, JSON `status` = `ok` |
| Web (if web deployed) | `GET {WEB}/` | 200 |
| Lookup | `GET {API}/api/v1/lookup?address={SMOKE_ADDRESS}` | 200, body includes `address_id` |
| Report | `GET {API}/api/v1/score/{address_id}` | 200 with report payload **or** documented computing status that still proves API+DB path |

Default `SMOKE_ADDRESS`: `609 SE Jamaica Dr, Bentonville, AR`

## 5. App env manifest

Path: `infra/deploy/app-env.manifest.json`

- Keys: `api`, `web` — arrays of env var names.
- Deploy must not write secret **values** into logs.
- Missing Actions/Key Vault mapping for a listed name → fail `app_config` job.
