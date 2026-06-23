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
