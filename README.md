# NeighborhoodInsight

Monorepo for the NeighborhoodInsight platform — Next.js frontend, FastAPI backend, data ingestion workers, and infrastructure.

## Quick start

**Local dev** (FastAPI + Next.js, no Docker):

```powershell
.\start.bat
# or
.\scripts\start.ps1
# or
npm run dev
```

**Full stack with Docker** (Postgres, Redis, API, web):

```powershell
.\scripts\start.ps1 -Mode docker
# or
npm run dev:docker
```

| URL | Service |
|-----|---------|
| http://localhost:3000 | Next.js frontend |
| http://localhost:8000/health | API health check |
| http://localhost:8000/api/docs | FastAPI Swagger UI |

The startup script creates `.env` from `.env.example` if needed, bootstraps `apps/api/.venv`, and runs both services in one terminal (via `concurrently`). Use `-Install` to refresh Python and npm dependencies.

## Local data workers (fixture counties)

Ingestion + scoring for the **10 canonical test addresses** only (county-scoped — not national). See `specs/002-data-ingestion-workers/quickstart.md`.

Suggested order against Compose:

```bash
docker compose up -d db redis api web
# Schema (existing volumes): infra/sql/002_*.sql, 003_*.sql, 004_safety_education_economic.sql
docker compose --profile workers run --rm worker-census
docker compose --profile workers run --rm worker-epa      # needs EPA_AQS_EMAIL / EPA_AQS_KEY
docker compose --profile workers run --rm worker-cms      # CMS public API + ZIP geocode
docker compose --profile workers run --rm worker-fbi      # needs FBI_CDE_API_KEY (safety)
docker compose --profile workers run --rm worker-nces     # public NCES EDGE schools
docker compose --profile workers run --rm worker-urban    # Urban CCD via LEAID (after NCES)
docker compose --profile workers run --rm worker-acs      # needs CENSUS_API_KEY
docker compose --profile workers run --rm worker-bls      # BLS LAUS (key optional)
docker compose --profile workers run --rm worker-scoring
```

Fixture addresses (Bentonville AR first) live in `workers/ingest/fixtures/canonical_addresses.py`. After scoring, search those addresses in the local app — reports read `neighborhood_scores` (vintage `2026-Q3`), not mock data.

## Branching

| Branch | Role |
|--------|------|
| `master` | Production — CI/CD deploys from here |
| `dev` | Integration / staging — spin up to test before prod |
| `NNN-feature-name` | Spec Kit feature work — always branch from **`dev`**, merge PRs back to **`dev`**, then promote `dev` → `master` for release |

Configured in `.specify/init-options.json` (`feature_base_branch`). Override with env `SPECIFY_FEATURE_BASE_BRANCH` if needed.

## Production hosting (Azure)

As-built Azure + GitHub Actions setup (glossary, CLI friction, CORS/DB URL gotchas, live inventory): [docs/azure-setup-and-cicd.md](docs/azure-setup-and-cicd.md). Design targets remain in [docs/nhiq-design-main/05-cicd.md](docs/nhiq-design-main/05-cicd.md) and [docs/nhiq-design-main/06-azure-infrastructure.md](docs/nhiq-design-main/06-azure-infrastructure.md).
