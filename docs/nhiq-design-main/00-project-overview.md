# NeighborhoodIQ — Project Overview

> **Read this file first before working on any part of the codebase.**
> It is the authoritative source of product context, architecture decisions, and conventions.

---

## What We're Building

NeighborhoodIQ is an AI-powered neighborhood intelligence platform. Given any U.S. address, it produces a comprehensive **Neighborhood Score** with plain-English AI narratives across five dimensions:

| Score Dimension | Data Sources |
|---|---|
| Healthcare Access | CMS (ER wait times, hospital quality, star ratings) |
| Safety & Environment | FBI Crime Data Explorer, EPA AQI, FEMA National Risk Index, EPA EJScreen |
| Education & Amenities | NCES schools, EPA Smart Location DB, USDA Food Atlas, OpenStreetMap |
| Economic Health | Zillow public CSVs, BLS unemployment, Census Business Formation |
| Overall / Composite | Weighted average, personalized by user profile |

The AI layer (Claude API) generates narratives, personalization, trade-off comparisons, and trend forecasts.

---

## Business Model

| Tier | Price | Notes |
|---|---|---|
| Free | $0 | 3 lookups/month, basic scores |
| Buyer | $19/mo | Unlimited lookups, full AI narratives, comparisons |
| Buyer Pro | $49/mo | + trend forecasting, PDF exports, priority support |
| Agent | $99/mo | White-labeled reports, agent branding |
| Brokerage | $499/mo | Team seats, API access, CRM integration |
| API | $0.50–$2.00/lookup | Pay-per-lookup for proptech/mortgage/insurance |

---

## Architecture Decisions (Locked)

These decisions are made. Do not propose alternatives unless explicitly asked.

1. **Monorepo** — single Git repo, all apps and workers in `apps/` and `workers/`
2. **Next.js 14** (App Router, TypeScript, Tailwind) — web and mobile-web frontend
3. **FastAPI** (Python 3.12) — API backend, all business logic lives here
4. **PostgreSQL 16 + PostGIS** — primary datastore with geospatial support
5. **Redis** — score cache (24h TTL), session store
6. **Azure Container Apps** — all containers deployed here (scales to zero)
7. **Azure Container Registry** — Docker image storage
8. **Azure Front Door + WAF** — CDN, routing, TLS termination
9. **Azure Blob Storage** — PDF report exports
10. **Azure Key Vault** — all secrets at runtime (no secrets in code or `.env` in prod)
11. **GitHub Actions** — CI/CD pipeline
12. **Claude API (claude-sonnet-4-20250514)** — narrative generation, personalization copy, trade-off explainer

---

## Repository Layout

```
neighborhoodiq/
├── apps/
│   ├── web/                        # Next.js 14 frontend
│   └── api/                        # FastAPI backend
├── workers/
│   ├── ingest/                     # Data ingestion (per source)
│   │   ├── cms/
│   │   ├── epa/
│   │   ├── fema/
│   │   ├── fbi/
│   │   ├── census/
│   │   └── zillow/
│   └── scoring/                    # ML scoring pipeline
├── packages/
│   └── shared-types/               # Shared TypeScript types (future)
├── docker/
│   ├── web.Dockerfile
│   ├── api.Dockerfile
│   └── worker.Dockerfile
├── infra/
│   └── bicep/                      # Azure IaC
├── docs/                           # This folder — instructions for Claude
├── .github/
│   └── workflows/
│       └── deploy.yml
├── docker-compose.yml              # Local dev
├── docker-compose.prod.yml         # Production overrides
├── .env.example                    # Template — committed
├── .env                            # Local secrets — gitignored
└── .gitignore
```

---

## URL Routing Convention

| Path | Service |
|---|---|
| `/*` | Next.js (Azure Front Door → web container) |
| `/api/v1/*` | FastAPI (Azure Front Door → api container) |
| Internal service-to-service | Use container name via Docker network |

The Next.js frontend never talks directly to the database or external APIs. All data goes through FastAPI.

---

## Environment Variables

| Variable | Used By | Description |
|---|---|---|
| `DATABASE_URL` | api, workers | `postgresql://user:pass@host:5432/neighborhoodiq` |
| `REDIS_URL` | api | `redis://host:6379` |
| `ANTHROPIC_API_KEY` | api | Claude API key |
| `MAPBOX_TOKEN` | api | Mapbox geocoding |
| `NEXT_PUBLIC_API_URL` | web | Base URL for API calls from browser |
| `NEXTAUTH_SECRET` | web | Auth.js secret |
| `NEXTAUTH_URL` | web | Full URL of web app |
| `AZURE_STORAGE_CONNECTION_STRING` | api | Blob storage for PDFs |

---

## API Versioning

All FastAPI routes are prefixed `/api/v1/`. When breaking changes are needed, add `/api/v2/` — do not modify v1 routes.

---

## Code Style & Conventions

### Python (FastAPI, workers)
- Python 3.12+
- `ruff` for linting, `black` for formatting
- Type hints everywhere — use Pydantic models for all request/response bodies
- Async route handlers (`async def`) for all I/O-bound operations
- Never put business logic in route handlers — route handlers call service functions in `services/`

### TypeScript (Next.js)
- Strict TypeScript (`"strict": true`)
- Tailwind for all styling — no CSS modules, no styled-components
- Server Components by default; add `"use client"` only when needed
- `zod` for runtime validation of API responses
- API calls via a typed `apiFetch` wrapper in `apps/web/lib/api.ts`

### Git
- Branch naming: `feat/short-description`, `fix/short-description`, `chore/short-description`
- Commit messages: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- PRs to `main` trigger CI/CD — do not push directly to `main`

---

## Development Phases

| Phase | Timeline | Goal |
|---|---|---|
| 1 — Build & Validate | Months 1–4 | Free tier live, top 50 metros, 500 active users |
| 2 — Monetize | Months 5–8 | Paid tiers live, $5K MRR, agent beta |
| 3 — B2B Expansion | Months 9–18 | Brokerage/API plans, $50K MRR, Series A ready |

---

## Key External API Endpoints (Reference)

| Source | Base URL | Auth |
|---|---|---|
| CMS Hospital Compare | `https://data.cms.gov/provider-data/api/1/datastore/query/` | None (public) |
| EPA AQS | `https://aqs.epa.gov/data/api/` | Email + key |
| EPA EJScreen | `https://ejscreen.epa.gov/mapper/ejscreenRESTbroker.aspx` | None |
| FEMA NRI | `https://hazards.fema.gov/nri/Content/StaticDocuments/DataDownload/` | None |
| FBI CDE | `https://api.usa.gov/crime/fbi/cde/` | API key |
| Census ACS | `https://api.census.gov/data/` | API key |
| Zillow | Public CSVs at `https://www.zillow.com/research/data/` | None |
| OpenStreetMap (osmnx) | Overpass API | None |

---

## Current Status

- [ ] Monorepo scaffold
- [ ] Docker local dev stack
- [ ] FastAPI skeleton with health check
- [ ] Next.js skeleton with address search UI
- [ ] PostgreSQL + PostGIS schema
- [ ] First ingestion worker (EPA AQI)
- [ ] Scoring pipeline v1
- [ ] Claude narrative generation
- [ ] Auth (Next Auth / Auth.js)
- [ ] Freemium gating middleware
- [ ] PDF export
- [ ] CI/CD pipeline
- [ ] Azure infrastructure (Bicep)
