# Azure setup and CI/CD (as-built)

This document describes **what we actually set up** for NeighborhoodInsight production hosting on Azure and continuous deploy from GitHub. It is written for someone new to Azure and cloud hosting, and is suitable to hand to an LLM that should walk through every step in plain language.

It is **not** a secret store. Never put passwords, tokens, or Key Vault values into this file (or into git). Describe *where* secrets live and *how* to set them.

## Related design docs (intended end-state)

| Doc | Role |
|-----|------|
| [docs/nhiq-design-main/06-azure-infrastructure.md](nhiq-design-main/06-azure-infrastructure.md) | Planned full Azure resource map (Container Apps, Postgres, Redis, Front Door, workers, Bicep, etc.) |
| [docs/nhiq-design-main/05-cicd.md](nhiq-design-main/05-cicd.md) | Planned CI/CD workflows (lint/test, deploy, workers, migrations) |

**This narrative = as-built path we followed.** The design docs = fuller target (workers, Front Door, automated migrations in CI). Prefer this file when explaining current prod; prefer the design docs when planning the next infrastructure slice.

---

## 1. Goals and mental model

**Goal:** A public website that tracks whatever is on the Git `master` branch. Push (or merge) to `master` → GitHub Actions builds Docker images → pushes them to Azure Container Registry (ACR) → updates Azure Container Apps so the live URLs serve the new code.

```text
  You (git push to master)
           │
           ▼
  GitHub Actions (Deploy workflow)
           │
           ├─ Build API image  ─┐
           ├─ Build web image  ─┼─► Azure Container Registry (ACR)
           │                    │
           └─ Deploy ───────────┴─► Container Apps (niq-api, niq-web)
                                      │
                                      ├─► Azure Postgres (data)
                                      └─► Azure Redis (cache)
```

**Important separations**

| Thing | Where | Notes |
|-------|--------|------|
| Git branch `master` | GitHub | Source of truth for *code* that goes to prod |
| Live web/API | Azure Container Apps | Running containers; updated by Deploy |
| Prod database | Azure Postgres Flexible Server | **Empty until you apply schema**; not the same as local Docker Postgres |
| Local Docker Postgres | Your laptop | Only for local/dev; test accounts do **not** copy to Azure |

**Branching (repo policy):** Spec Kit features normally PR into `dev`, then promote `dev` → `master` for release. Deploy today triggers on **`master` only** (see [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)).

---

## 2. Glossary (Azure & deploy jargon)

| Term | Plain meaning |
|------|----------------|
| **Subscription** | Billing container in Azure (ours: `NHIQ-testing`). Everything you create is charged to a subscription. |
| **Resource group** | Named folder for related resources (ours: `neighborhoodiq-rg`). Easy to list or delete as a group. |
| **Region** | Azure data-center geography (`eastus`, `centralus`, …). Not all products are allowed in every region for every subscription. |
| **Resource provider** | Azure “product plugin” (`Microsoft.ContainerRegistry`, `Microsoft.App`, …). Must be **Registered** on the subscription before you can create that product’s resources. |
| **ACR (Azure Container Registry)** | Private Docker Hub–like registry for *your* images. |
| **Container App** | Managed place to run a container with a public HTTPS URL (ingress). |
| **Container Apps Environment** | Shared networking/hosting plane for several Container Apps. |
| **Revision** | A version of a Container App’s config+image. Changing env vars or nudging deploy creates a new revision; **secrets often require a restart / new revision** to take effect. |
| **PostgreSQL Flexible Server** | Managed Postgres (ours: auth + app tables). |
| **Redis (Azure Cache)** | Managed Redis for cache / rate limits. |
| **Key Vault** | Locked box for secrets (DB URL, API keys). Access is via **RBAC** roles (e.g. Key Vault Secrets Officer). |
| **Storage account** | Blob storage (e.g. PDF reports later). |
| **Service principal** | Robot Azure identity GitHub Actions uses instead of your personal login. JSON from `az ad sp create-for-rbac` becomes the `AZURE_CREDENTIALS` GitHub secret. |
| **GitHub Actions secrets** | Encrypted values under Repo → Settings → Secrets and variables → Actions. Workflows read them as `${{ secrets.NAME }}`. |
| **CORS** | Browser rule: a page on origin A may only call API on origin B if the API allows origin A in headers. Wrong/missing CORS (or a 500 without CORS headers) looks like “blocked by CORS” in DevTools. |
| **`DATABASE_URL`** | Connection string the API uses to talk to Postgres. |
| **`sslmode` vs `ssl`** | Classic `psql` / many libs use `?sslmode=require`. Our API uses **SQLAlchemy + asyncpg**, which expects **`?ssl=require`**. Using `sslmode` causes: `connect() got an unexpected keyword argument 'sslmode'`. |
| **FQDN** | Fully qualified domain name, e.g. `niq-web....azurecontainerapps.io`. |

---

## 3. Starting point (what already existed)

| Item | Value |
|------|--------|
| Subscription | `NHIQ-testing` |
| Resource group | `neighborhoodiq-rg` |
| Resource group region | East US (`eastus`) |

CLI login (PowerShell):

```powershell
az login
az account set --subscription "NHIQ-testing"
az account show -o table
```

Install Azure CLI on Windows if needed ([Microsoft docs](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows)). Container Apps needs the extension:

```powershell
az extension add --name containerapp --upgrade
```

---

## 4. Register resource providers

New subscriptions often return `MissingSubscriptionRegistration` or mysterious `SubscriptionNotFound` until providers are registered.

Examples we hit:

```powershell
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.Cache
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.KeyVault
```

Poll until state is `Registered`:

```powershell
az provider show --namespace Microsoft.ContainerRegistry --query registrationState -o tsv
```

Often takes **1–5 minutes**. `NotRegistered` means register again (or use Portal → Subscription → Resource providers).

---

## 5. Azure Container Registry (ACR)

**Why:** GitHub Actions (and manual builds) push Docker images here; Container Apps pull from here.

```powershell
$RG = "neighborhoodiq-rg"
$LOCATION = "eastus"
$ACR_NAME = "neighborhoodiqacr"   # globally unique; letters/numbers only

az acr create `
  --resource-group $RG `
  --name $ACR_NAME `
  --sku Basic `
  --admin-enabled true `
  --location $LOCATION
```

Save credentials for GitHub later (do not commit them):

```powershell
az acr show --name $ACR_NAME --resource-group $RG --query loginServer -o tsv
az acr credential show --name $ACR_NAME --resource-group $RG
```

ACR returns **password** and **password2** — either works for login.

As-built login server: `neighborhoodiqacr.azurecr.io`.

---

## 6. Log Analytics + Container Apps Environment

**Why:** Container Apps need a Log Analytics workspace for logs; an **Environment** is the shared host for `niq-api` and `niq-web`.

Create workspace `niq-logs`, then environment `niq-env` in East US (see design doc Step 3–4 for the full CLI). Capture workspace customer ID and shared key for `az containerapp env create`.

### Friction we hit (East US)

| Symptom | What it meant | What we did |
|---------|---------------|-------------|
| `AKSCapacityHeavyUsage` | Azure short on capacity for the ACA backend in East US | Retry later |
| CLI error after ~13 min + HTML “services aren’t available” | Control plane flake while polling | Env may still exist — check `az containerapp env list` |
| Env stuck `Updating`, `health: null` for a long time | Half-provisioned / stuck | Delete and recreate |
| Cannot create second env name in same region | Quota: **max 1 Container Apps Environment per region per subscription** | Wait until delete finishes, then create one env |

Final as-built: Environment **`niq-env`** in **East US**, `Succeeded`.

---

## 7. Data tier: Postgres + Redis

### Postgres Flexible Server

- Desired design location was East US; **create failed** with *location is restricted* for our subscription.
- As-built: Postgres in **`centralus`** (first region that accepted create). Server name: `niq-postgres`, admin user: `niqadmin`, database: `neighborhoodiq`.

CLI flags to remember (Azure CLI naming is inconsistent across commands):

| Operation | Gotcha |
|-----------|--------|
| Create DB | Database name is `--name`, not `--database-name` |
| Firewall rule | Rule name is `--name`; server is `--server-name` |

Allow Azure-hosted services (testing; tighten for real production later):

```powershell
az postgres flexible-server firewall-rule create `
  --resource-group $RG `
  --server-name niq-postgres `
  --name AllowAzureServices `
  --start-ip-address 0.0.0.0 `
  --end-ip-address 0.0.0.0
```

To run SQL from your laptop, also allow **your public IP** (rule name e.g. `AllowMyClient`).

### Extensions and schema

`infra/sql/init.sql` needs PostGIS and `uuid-ossp`. Azure blocks them until allow-listed:

```powershell
az postgres flexible-server parameter set `
  --resource-group $RG `
  --server-name niq-postgres `
  --name azure.extensions `
  --value "POSTGIS,UUID-OSSP"
```

Then apply schema. You do **not** need Postgres installed on Windows. Use a throwaway client container (talks to **Azure**, not your local `docker compose` volume):

```powershell
cd "C:\Users\ruben\Git Projects\nhiq-mono"

docker run --rm -i `
  -e PGPASSWORD="YOUR_AZURE_PG_PASSWORD" `
  -v "${PWD}/infra/sql:/sql" `
  postgres:16 `
  psql "host=niq-postgres.postgres.database.azure.com port=5432 dbname=neighborhoodiq user=niqadmin sslmode=require" `
  -f /sql/init.sql
```

Success looks like a series of `CREATE EXTENSION` / `CREATE TABLE` / `CREATE INDEX` lines.

**Local Docker Postgres vs Azure:** Completely separate. Registering a user on prod writes only to Azure. Local test users never appear in Azure unless you seed Azure deliberately.

### Redis

As-built: **`niq-redis`** in **East US** (same region as Container Apps for lower latency). Prefer East US for Redis; put it next to Postgres only if East US create fails.

---

## 8. Storage + Key Vault

### Storage

Create a globally unique storage account name (letters/numbers only), then a private container `reports` for future PDF exports. Save the connection string into Key Vault as `AZURE-STORAGE-CONNECTION-STRING`.

If create fails with `SubscriptionNotFound` while `az account show` looks fine, register **`Microsoft.Storage`** and retry.

### Key Vault

As-built vault name example: `niq-kv-21698` (must be globally unique).

Modern Key Vaults use **RBAC**. Creating the vault does **not** automatically let you write secrets. Assign yourself **Key Vault Secrets Officer** on the vault scope, wait 1–2 minutes for propagation, then `az keyvault secret set`.

Secrets we stored (names only):

| Secret name | Purpose |
|-------------|---------|
| `DATABASE-URL` | API → Postgres (see §12 for `ssl=` vs `sslmode=`) |
| `REDIS-URL` | API → Redis (`rediss://...`) |
| `AZURE-STORAGE-CONNECTION-STRING` | Blob storage |
| `NEXTAUTH-SECRET` / app auth secrets | Web Auth.js |
| `SECRET-KEY` | API JWT signing |
| `MAPBOX-TOKEN` | API Mapbox |
| `NEXT-PUBLIC-MAPBOX-TOKEN` | Web public Mapbox (also used as CI build secret) |

Anthropic was **skipped** until narratives ship.

---

## 9. First images (manual Docker)

Apps already had Dockerfiles: [`docker/api.Dockerfile`](../docker/api.Dockerfile), [`docker/web.Dockerfile`](../docker/web.Dockerfile). Build context = **repo root**. Prefer `--platform linux/amd64` for Azure.

1. `az acr login --name neighborhoodiqacr`
2. Build/push API (`--target runtime`), tag `neighborhoodiqacr.azurecr.io/neighborhoodiq-api:latest`
3. Create `niq-api` Container App, learn its FQDN
4. Build web with build-args:
   - `NEXT_PUBLIC_API_URL=https://<api-fqdn>`
   - `NEXT_PUBLIC_MAPBOX_TOKEN=...`
5. Push web, create `niq-web`

Cached layers can make a “build” finish in seconds — that is normal if you already built locally.

---

## 10. Container Apps: secrets, env vars, revisions

### Apps (as-built)

| App | Port | Public URL pattern |
|-----|------|--------------------|
| `niq-api` | 8000 | `https://niq-api.<env-hash>.eastus.azurecontainerapps.io` |
| `niq-web` | 3000 | `https://niq-web.<env-hash>.eastus.azurecontainerapps.io` |

Health check: `GET /health` on the API.

### Secrets pattern

Container Apps store secrets separately from env vars. Env vars reference secrets with `secretref:name`:

```text
DATABASE_URL=secretref:database-url
```

**Critical:** `az containerapp secret set` often **replaces the entire secret set**. When adding a secret, re-pass **all** secrets you still need (`database-url`, `redis-url`, `mapbox-token`, `secret-key`, …).

Redis URLs contain `://`, `:`, `@` — quote carefully so the CLI does not truncate the value.

### Secrets need a restart

Azure warns: *Container App must be restarted for secret changes to take effect.* Check revisions:

```powershell
az containerapp revision list `
  --name niq-api `
  --resource-group neighborhoodiq-rg `
  --query "[].{name:name, active:properties.active, created:properties.createdTime}" `
  -o table
```

Reliable ways to pick up new secrets:

- `az containerapp revision restart --name niq-api --resource-group ... --revision <active-revision>`
- Or force a new revision by changing an env var (e.g. `RESTART_NUDGE=1`) via `az containerapp update --set-env-vars`
- Revision names typically increment (`niq-api--0000007` → `--0000008`). If the number never changes, the app may not have recycled.

Web env we set: `NEXTAUTH_SECRET` / `AUTH_SECRET`, `NEXTAUTH_URL` / `AUTH_URL` (public web URL), `API_INTERNAL_URL` (API HTTPS FQDN).

---

## 11. CORS (browser register/login)

API defaults in [`apps/api/app/core/config.py`](../apps/api/app/core/config.py) only allow localhost and a future custom domain — **not** the `*.azurecontainerapps.io` web origin.

Set env on `niq-api` as a **JSON list** (Portal is often safer than PowerShell quoting):

```text
CORS_ORIGINS=["https://niq-web.blackstone-0becc01d.eastus.azurecontainerapps.io","http://localhost:3000","https://nh-iq.com"]
```

Verify with OPTIONS; allowed origins get `access-control-allow-origin`. Starlette returns **400** on preflight when the origin is **not** allow-listed (often *without* that header).

**Browser trap:** A real **500** on POST may still show as “blocked by CORS” because the error response lacks CORS headers. Always check Network status code and API logs:

```powershell
az containerapp logs show --name niq-api --resource-group neighborhoodiq-rg --tail 100
```

---

## 12. DATABASE_URL gotchas (asyncpg + PowerShell)

Code converts `postgresql://...` → `postgresql+asyncpg://...` in [`apps/api/app/db/session.py`](../apps/api/app/db/session.py).

| Wrong | Right (for our API) |
|-------|---------------------|
| `?sslmode=require` | `?ssl=require` |

Error if wrong: `TypeError: connect() got an unexpected keyword argument 'sslmode'`.

Other pitfalls:

- Password special characters: prefer Portal “Reset password”, then set Key Vault / Container App secret with **single-quoted** PowerShell strings.
- URL-encode the password segment with `[uri]::EscapeDataString($password)` before putting it in `DATABASE_URL`.
- `psql` can succeed while the app fails if the URL encoding / `ssl=` flag differs.

Shape (placeholders only):

```text
postgresql://niqadmin:<urlencoded-password>@niq-postgres.postgres.database.azure.com:5432/neighborhoodiq?ssl=require
```

Copy that into Key Vault `DATABASE-URL` **and** Container App secret `database-url`, then restart / new revision.

---

## 13. CI/CD (GitHub Actions → Azure)

### Service principal

```powershell
$SUB_ID = az account show --query id -o tsv
$RG = "neighborhoodiq-rg"

az ad sp create-for-rbac `
  --name "neighborhoodiq-github-actions" `
  --role contributor `
  --scopes "/subscriptions/$SUB_ID/resourceGroups/$RG" `
  --sdk-auth
```

Paste the **entire JSON** into GitHub secret `AZURE_CREDENTIALS` (never commit it).

### GitHub repository secrets (as-built)

| Secret | Purpose |
|--------|---------|
| `AZURE_CREDENTIALS` | Service principal JSON for `azure/login` |
| `ACR_LOGIN_SERVER` | e.g. `neighborhoodiqacr.azurecr.io` |
| `ACR_USERNAME` | ACR admin username |
| `ACR_PASSWORD` | ACR admin password |
| `AZURE_RESOURCE_GROUP` | `neighborhoodiq-rg` |
| `AZURE_CONTAINER_APP_API` | `niq-api` |
| `AZURE_CONTAINER_APP_WEB` | `niq-web` |
| `NEXT_PUBLIC_API_URL` | Public API HTTPS URL (web build arg) |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Web build arg |

### Workflow

File: [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml).

| Trigger | Behavior |
|---------|----------|
| `push` to `master` | Build+push API & web images, deploy both apps |
| `workflow_dispatch` | Manual run from Actions UI |

Jobs: **Build & Push to ACR** → **Deploy API** → **Deploy Web**. First successful run was on the order of ~9 minutes. Ignore Node.js 16 deprecation *warnings* unless a job actually fails.

Watch runs: https://github.com/rubenmathew24/nhiq-mono/actions

After a green Deploy Web, hard-refresh the live site (`Ctrl+Shift+R`) — CDN/browser cache can show old UI briefly.

---

## 14. Current prod inventory (as-built)

Values can change if resources are recreated; confirm in Portal or CLI when unsure.

| Resource | Name / value | Region |
|----------|----------------|--------|
| Subscription | `NHIQ-testing` | — |
| Resource group | `neighborhoodiq-rg` | East US (metadata) |
| ACR | `neighborhoodiqacr` → `neighborhoodiqacr.azurecr.io` | East US |
| Log Analytics | `niq-logs` | East US |
| Container Apps Environment | `niq-env` | East US |
| API app | `niq-api` | East US |
| Web app | `niq-web` | East US |
| Web FQDN | `https://niq-web.blackstone-0becc01d.eastus.azurecontainerapps.io` | — |
| API FQDN | `https://niq-api.blackstone-0becc01d.eastus.azurecontainerapps.io` | — |
| Postgres | `niq-postgres` / DB `neighborhoodiq` / admin `niqadmin` | **Central US** |
| Redis | `niq-redis` | East US |
| Key Vault | `niq-kv-21698` (example; use your vault name) | East US |
| Storage | `niqstorage*****` (random suffix) | East US |
| Deploy workflow | `.github/workflows/deploy.yml` on `master` | — |
| Worker image | `neighborhoodiq-worker:dev` in ACR | Hand-pushed (not Deploy.yml) |
| Worker jobs | `niq-worker-*` (9 manual ACA Jobs) | See §16 |

---

## 15. Design docs vs reality (cheat sheet)

| Topic | Design docs | As-built today |
|-------|-------------|----------------|
| Regions | Largely East US | Env/apps/Redis/ACR East US; **Postgres Central US** |
| IaC | Bicep under `infra/bicep/` | Mostly Azure CLI / Portal |
| CI | Separate `ci.yml` + `deploy.yml` + workers | **Deploy only** on `master` |
| Migrations | Alembic job in CI | Manual `init.sql` against Azure |
| Workers / Front Door / Key Vault→ACA identity | Specified | **Workers: manual ACA Jobs wired (see §16)**; Front Door / KV→ACA identity still not wired |
| Image promotion | Tag by git SHA + `latest` | API/web via Deploy on `master`; **worker image pushed by hand** to ACR tag `neighborhoodiq-worker:dev` |
| Ingest schema | Design raw tables | Azure has `init.sql` + manual `002` / `003` / `004` applied |
| National ingest | Design 50-state loops | **Not done.** Jobs currently scoped to fixture counties via optional `INGEST_COUNTY_ALLOWLIST` |

When you extend prod, update **this** file with what you actually did, and keep the design docs as the longer-term target unless you deliberately change the constitution/stack.

---

## 16. Worker Container Apps Jobs (as-built)

Ingest workers write **directly** to Azure Postgres (`niq-postgres` / `neighborhoodiq`). They do **not** go through the `master` Deploy workflow.

### Image and secrets

| Item | As-built |
|------|----------|
| Image | `neighborhoodiqacr.azurecr.io/neighborhoodiq-worker:dev` (build from worker branch with `docker/worker.Dockerfile`, `az acr login`, push) |
| Worker DB URL | Key Vault `WORKER-DATABASE-URL` — **`?sslmode=require`** (psycopg2). Do **not** reuse API `DATABASE-URL` (`?ssl=require` / asyncpg) |
| Other KV secrets | `EPA-AQS-EMAIL`, `EPA-AQS-KEY`, `FBI-CDE-API-KEY`, `CENSUS-API-KEY` (as needed) |
| Scope env | `INGEST_COUNTY_ALLOWLIST` — comma-separated SSCCC FIPS; **empty/unset = all checked-in fixture counties**; set e.g. `05007` for a one-county smoke |

### Manual jobs (resource group `neighborhoodiq-rg`, env `niq-env`)

`niq-worker-geo`, `niq-worker-orchestrate`, `niq-worker-census`, `niq-worker-epa`, `niq-worker-cms`, `niq-worker-fbi`, `niq-worker-nces`, `niq-worker-urban`, `niq-worker-acs`, `niq-worker-bls`, **`niq-worker-fema`**, **`niq-worker-cms-timely`**, `niq-worker-scoring`, **`niq-worker-status`**.

Shape: trigger **Manual**, ~1 CPU / 2Gi, `--replica-timeout` 7200s (status/geo can use 600–3600s). Command form: `python` `-m` `<module>` (e.g. `ingest.geo.run`, `ingest.census.run`, `ingest.fema.run`, `ingest.cms_timely.run`, `scoring.compute`, **`ingest.status`**).

### Creating report-detail jobs (FEMA + CMS Timely)

If missing, create like other ingest jobs (same image `neighborhoodiqacr.azurecr.io/neighborhoodiq-worker:dev`, same `WORKER-DATABASE-URL` secretref):

| Job | Command |
|-----|---------|
| `niq-worker-fema` | `python` `-m` `ingest.fema.run` |
| `niq-worker-cms-timely` | `python` `-m` `ingest.cms_timely.run` |

No new API keys (public FEMA FeatureServer + CMS Provider Data Catalog). Rebuild/push the worker image after merging report-detail national support, then point both jobs at that tag.

Status job env: `INGEST_SCOPE=metro_10` (or `smoke` / `national`), optional `INGEST_COUNTY_ALLOWLIST`, `DATABASE_URL` → `WORKER-DATABASE-URL`.

### Report-detail promote → Azure smoke gate (before National Ingest)

1. Merge feature to `dev`, promote `dev` → `master`; wait for Deploy (API/web) and rebuild/push the **worker** image used by ACA jobs.
2. Apply [`infra/sql/007_report_detail.sql`](../infra/sql/007_report_detail.sql) on Azure Postgres (idempotent). Confirm `acs_indicators.total_population` exists (from `004` / init).
3. Ensure `niq-worker-fema` and `niq-worker-cms-timely` exist (table above).
4. **Smoke fill** (Benton County): set `INGEST_SCOPE=smoke` on acs / fema / cms_timely / scoring (or allowlist `05007`), then start in order:

```powershell
az containerapp job start --name niq-worker-acs --resource-group neighborhoodiq-rg
az containerapp job start --name niq-worker-fema --resource-group neighborhoodiq-rg
az containerapp job start --name niq-worker-cms-timely --resource-group neighborhoodiq-rg
az containerapp job start --name niq-worker-scoring --resource-group neighborhoodiq-rg
```

5. Open production web → `609 SE Jamaica Dr, Bentonville, AR` → expand report must match the known-good local/dev expand UI (sub-scores, plain-English stats, hazard/wait when sources provided).
6. **If smoke fails, do not start National Ingest.** Local Compose alone does not clear this gate.

See also [`specs/005-national-report-detail/quickstart.md`](../specs/005-national-report-detail/quickstart.md).

### National ingest (50 states + DC, phased)

See also [`specs/003-national-ingest/quickstart.md`](../specs/003-national-ingest/quickstart.md).

1. Apply [`infra/sql/006_geo_counties.sql`](../infra/sql/006_geo_counties.sql) (and **`007_report_detail.sql`** if not already applied for expand reports).
2. Bootstrap registry (all included jurisdictions): `INGEST_GEO_LOAD_ALL=1` on `niq-worker-geo`, then start it.
3. **Preferred:** GitHub → Actions → **National ingest** → Run workflow (`max_states`, optional `state_filter`, optional `force_states`). This starts `niq-worker-orchestrate`, which inventories DB gaps (including FEMA, CMS Timely, ACS population, and empty `score_detail`) and only starts ACA jobs that still need work—or force-reruns all workers for states listed in `force_states`. **`force_states` / `state_filter` are exclusive lists** (no padding other gap states to fill `max_states`).
4. **No force required for report-detail backfill:** states that already finished base ingest but lack hazard/timely/pop/`score_detail` remain gap states. Orchestrator **prefers** those states over virgin states when filling `max_states`. For a selected state it runs only missing stages (e.g. `fema` → `cms_timely` → `scoring`), not a full census…bls redo.
5. Manual fallback: set on ingest/scoring jobs `INGEST_SCOPE=national`, `INGEST_STATE_BATCH=<SS>`; run workers in order; re-start to resume (`skip_checkpoint`). Set `INGEST_FORCE=1` to re-upsert without skip-done (formula changes / bad data only).
6. Status with `INGEST_SCOPE=national` for Workbook % against full `geo_counties` universe (includes `fema` / `cms_timely`). Orchestrator emits slim `INGEST_STATUS_SNAPSHOT` after each worker. Re-import [`infra/workbook-ingest-status.json`](../infra/workbook-ingest-status.json) if the gallery is stale (jobs table expands dynamically).
7. Territories are **not** in v1; enable later by moving FIPS from `TERRITORY_STATE_FIPS` → `INCLUDED_STATE_FIPS` in code.

Orchestrator job: `niq-worker-orchestrate`. GitHub Actions **National ingest** injects the Deploy service principal from `AZURE_CREDENTIALS` into the job env on each run (no separate Key Vault SP required). The SP must be able to start/update jobs in the RG. **Do not** wire national ingest to the `master` Deploy workflow. Workflow inputs unchanged — new jobs are discovered via worker inventory code.

### Ingest progress Workbook (ops)

Data completion % is **not** ACA “Running”. Snapshot source of truth:

1. Apply [`infra/sql/005_ingest_status.sql`](../infra/sql/005_ingest_status.sql) on Azure Postgres.
2. Start status job (writes `ingest_status_snapshot` + prints `INGEST_STATUS_SNAPSHOT {...}` for Log Analytics):

```powershell
az containerapp job start --name niq-worker-status --resource-group neighborhoodiq-rg
```

3. Import workbook gallery JSON [`infra/workbook-ingest-status.json`](../infra/workbook-ingest-status.json):
   - Portal → Log Analytics workspace **`niq-logs`** → **Workbooks** → **New** / **Advanced editor** → paste JSON → **Save** as “NeighborhoodInsight ingest status”.
   - Bind the workbook to `niq-logs`. Table name may be `ContainerAppConsoleLogs_CL` or `ContainerAppConsoleLogs` depending on diagnostic schema — adjust the KQL if empty.
4. Spot-check SQL (Docker `psql` as in §7):

```sql
SELECT job_name, pct_complete, done_count, total_count, captured_at
FROM ingest_status_snapshot
WHERE scope = 'metro_10'
ORDER BY job_name;
```

Scoring % = tracts with `score_sources.safety.source_id = 'fbi_cde'` **and** non-empty `score_detail` / tracts in scope. Status also reports `fema` and `cms_timely` completion.

### Run order and resume

```text
census → epa → cms → fbi → nces → urban → acs → bls → fema → cms_timely → scoring
# anytime: status (refresh Workbook)
```

Upserts are idempotent — re-start a failed job, then re-run scoring if needed. Do not truncate.

```powershell
az containerapp job start --name niq-worker-census --resource-group neighborhoodiq-rg
az containerapp job execution list --name niq-worker-census --resource-group neighborhoodiq-rg -o table
```

### Schema on Azure (workers)

Applied manually (in order) when missing: `infra/sql/init.sql`, `002_raw_ingest_tables.sql`, `003_score_sources.sql`, `004_safety_education_economic.sql`, **`005_ingest_status.sql`**, **`006_geo_counties.sql`**, **`007_report_detail.sql`** (`score_detail`, `fema_nri_tracts`, `hospital_timely_measures`). Confirm `acs_indicators.total_population` (004/init). Same Docker `psql` + `sslmode=require` pattern as §7. **Do not truncate** existing national data.

### Explicitly deferred

- US territories in national universe (registry designed to add later)
- Cron schedules on jobs
- Worker image build in GitHub Actions / promote via `master`
- Front Door; Key Vault managed-identity wiring to ACA
- In-app product UI for ingest status (reuse `ingest_status_snapshot` later)

---

## Quick recovery checklist

1. **Site loads but auth 500 + “CORS”** → API logs; schema missing? extensions allow-listed? `DATABASE_URL` `ssl=`? password match? revision restarted?
2. **OPTIONS CORS 400** → `CORS_ORIGINS` missing Azure web origin.
3. **Deploy green but old UI** → hard refresh; confirm Deploy Web used new image tag / SHA.
4. **Secret change “did nothing”** → confirm active revision number incremented or restart; re-list all secrets after `secret set`.
5. **Cannot create second ACA environment in East US** → delete the old one first (quota = 1 per region).
