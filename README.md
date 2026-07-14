# NeighborhoodIQ

Monorepo for the NeighborhoodIQ platform — Next.js frontend, FastAPI backend, data ingestion workers, and infrastructure.

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

## Branching

| Branch | Role |
|--------|------|
| `master` | Production — CI/CD deploys from here |
| `dev` | Integration / staging — spin up to test before prod |
| `NNN-feature-name` | Spec Kit feature work — always branch from **`dev`**, merge PRs back to **`dev`**, then promote `dev` → `master` for release |

Configured in `.specify/init-options.json` (`feature_base_branch`). Override with env `SPECIFY_FEATURE_BASE_BRANCH` if needed.

## Production hosting (Azure)

As-built Azure + GitHub Actions setup (glossary, CLI friction, CORS/DB URL gotchas, live inventory): [docs/azure-setup-and-cicd.md](docs/azure-setup-and-cicd.md). Design targets remain in [docs/nhiq-design-main/05-cicd.md](docs/nhiq-design-main/05-cicd.md) and [docs/nhiq-design-main/06-azure-infrastructure.md](docs/nhiq-design-main/06-azure-infrastructure.md).
