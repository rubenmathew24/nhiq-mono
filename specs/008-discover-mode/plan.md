# Implementation Plan: Discover Mode (City Score Map)

**Branch**: `008-discover-mode` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-discover-mode/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Ship a public **Discover** POC: header tab → place autocomplete (city/locality) → locked Mapbox map colored by **relative overall neighborhood score** across census tracts in the selected place’s bbox. FastAPI returns precomputed tract GeoJSON + scores for an intersecting bbox (PostGIS); Next.js renders choropleth, legend, popups, and partial/empty coverage messaging. No auth, no saving Discover searches, overall score only.

## Technical Context

**Language/Version**: TypeScript (Next.js App Router) + Python 3.12 (FastAPI)

**Primary Dependencies**: Next.js, Tailwind, Mapbox GL JS (`mapbox-gl` already in web), Mapbox Places (browser `pk` token), FastAPI, SQLAlchemy/asyncpg or existing DB session patterns, PostGIS, Pydantic, Vitest, pytest

**Storage**: PostgreSQL 16 + PostGIS — read `census_tracts` + `neighborhood_scores` (active `SCORE_DATA_VINTAGE`). No new durable tables for Discover POC. Redis optional cache-aside for bbox responses (nice-to-have; not required for acceptance).

**Testing**: `apps/api/tests/` (pytest) for discover service/endpoint; `apps/web/src/__tests__/` (Vitest) for search navigation helpers / relative-color utility / empty states

**Target Platform**: Web (desktop primary demo; mobile basic usable)

**Project Type**: Monorepo web app + API (`apps/web`, `apps/api`)

**Performance Goals**: Typical large U.S. city demo place loads overlay without multi-second UI freezes; API targets ~1–2s for moderate tract counts with simplified geometry

**Constraints**: Constitution thin-client (no client DB/scoring); only Mapbox Places (+ Mapbox GL tiles/styles already used by report map) from browser; public endpoint (no freemium gate); clear user-facing errors; map locked to place bbox; relative coloring among scored tracts in view

**Scale/Scope**: POC — one Discover entry page + map page, one public tracts-in-bbox API, header link; no dimension toggles, no report deep-link, no city-polygon ingest

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodInsight Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**: Next.js + FastAPI + PostGIS + Mapbox; code under `apps/web` and `apps/api` only for this POC
- [x] **II. Thin Client, Fat API**: Tract query + score join in FastAPI `services/`; web uses `apiFetch` for overlay data; browser Mapbox Places for place autocomplete (allowed carve-out); Mapbox GL for basemap (existing report pattern)
- [x] **III. Precomputed Data Path**: Serves `neighborhood_scores` + stored tract geometries; no inline scoring or government fetches on request
- [x] **IV. API Contracts & Versioning**: New public route under `/api/v1/discover/...`; Pydantic models; zod on web for response validation where consumed
- [x] **V. Security & Secrets**: Public `pk` Mapbox token only in web; no new secrets; parameterized bbox SQL; validate bbox ranges / size
- [x] **VI. Test Alongside Features**: API + web tests planned with feature
- [x] **VII. Observability & Graceful Degradation**: Structured logs on discover queries; Redis (if used) fail-open to Postgres; missing scores → gray/empty UX not 500
- [x] **VIII. Clear User-Facing Errors**: Invalid bbox / no place / API failure → specific messages; empty coverage is an expected state with dedicated copy, not “Something went wrong”

## Project Structure

### Documentation (this feature)

```text
specs/008-discover-mode/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── discover-api.md
└── tasks.md             # /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
apps/web/src/
├── app/discover/              # entry + map routes
├── components/discover/       # place search, choropleth map, legend, banners
├── content/                   # navLinks + Discover copy
├── lib/                       # relative color helpers, discover types/zod
└── __tests__/
apps/api/app/
├── api/v1/endpoints/discover.py
├── api/v1/router.py           # include discover router
├── services/discover_service.py
├── schemas/discover.py        # Pydantic request/response
└── tests/test_discover*.py
```

**Structure Decision**: Thin web client + FastAPI discover service; reuse existing `mapbox-gl` and Places token patterns; no workers/migrations required for POC.

## Complexity Tracking

> No constitution violations requiring justification.
