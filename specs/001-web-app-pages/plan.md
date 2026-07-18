# Implementation Plan: Web App Pages

**Branch**: `001-web-app-pages` (feature dir; create/switch git branch at implement time) | **Date**: 2026-07-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-web-app-pages/spec.md`. Auth persistence now targets **Docker Compose PostgreSQL** (PostGIS) before merge to `master`.

## Summary

Ship the missing web surfaces (login, register, user menu, **signed-in upgrade/plans page**, dashboard with address search, compare **coming-soon placeholder**) while matching existing splash/report styling. Auth and saved-lookup APIs are implemented in FastAPI behind `/api/v1/*`. **Before merge**, replace the temporary JSONL file store with **Postgres repositories** against the local Docker Compose `db` service (`DATABASE_URL`, tables from `infra/sql/init.sql` / design schema). Keep `UserStore` / `LookupStore` protocols and `/api/v1` shapes stable. The web app stays thin: Auth.js credentials + `apiFetch`, shared Header/UserMenu chrome. `/pricing` is auth-gated **UI-only** upgrade (no billing). Live compare is deferred.

## Technical Context

**Language/Version**: TypeScript (Next.js App Router in `apps/web`, currently Next 16.x in repo) + Python 3.12 (FastAPI in `apps/api`)

**Primary Dependencies**: Next.js, Tailwind, Auth.js (next-auth v5), zod, `apiFetch`; FastAPI, Pydantic, JWT (python-jose + passlib/bcrypt); SQLAlchemy 2.0 + asyncpg (+ Alembic for migrations as needed)

**Storage**: **PostgreSQL 16 + PostGIS** via Docker Compose service `db` (`postgresql://postgres:postgres@db:5432/neighborhoodiq` in compose; localhost mapping for host-run API). Tables: `users`, `address_lookups`, `saved_lookups` per `infra/sql/init.sql` and `docs/nhiq-design-main/08-database-schema.md`. TEMP JSONL under `apps/api/data/` is **removed** in this feature before merge. Score/report data continues via existing score API / mocks / Redis where already wired.

**Testing**: Vitest + Testing Library for web (`apps/web/src/__tests__/`); pytest for API auth against Postgres (compose or test DB fixtures) in `apps/api/tests/`

**Target Platform**: Local Docker Compose / browser (desktop + mobile web)

**Project Type**: Monorepo web application (Next.js frontend + FastAPI backend)

**Performance Goals**: Auth form submit feedback under 2s locally; page navigations feel instant; no government API calls on these pages

**Constraints**: Match existing visual system; no Stripe; email/password only; no Azure Postgres required for this feature (local Docker only); secrets in gitignored `.env`; **Compose `web` image must be rebuilt after frontend auth chrome changes** (no source bind-mount — stale images reintroduce splash-only `#pricing` CTAs)


**Scale/Scope**: Local Docker demo; pages: `/login`, `/register`, `/pricing`, `/dashboard`, `/compare` (coming soon) + Header/UserMenu/Footer auth; splash `#pricing` auth-aware; report Back to dashboard when signed in

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodInsight Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**: Next.js + FastAPI + existing monorepo layout; Postgres via Docker Compose
- [x] **II. Thin Client, Fat API**: Auth/register/login/lookups live in FastAPI services; web uses `apiFetch` + Auth.js session chrome only
- [x] **III. Precomputed Data Path**: New pages do not ingest government data or compute scores; dashboard consumes existing score/report contracts or fixtures; live compare deferred
- [x] **IV. API Contracts & Versioning**: `/api/v1/auth/*`, `/api/v1/users/me`, lookups list under v1; Pydantic request/response models unchanged across store swap
- [x] **V. Security & Secrets**: Passwords hashed (bcrypt) in Postgres `users.hashed_password`; JWT secret from env; UI gates are UX — API still checks session
- [x] **VI. Test Alongside Features**: Auth API + Postgres-backed store tests; web tests for auth forms, UserMenu, pricing/dashboard, compare coming soon
- [x] **VII. Observability & Graceful Degradation**: Log auth failures at WARNING; empty `saved_lookups` → empty dashboard; no new streaming infra
- [x] **VIII. Clear User-Facing Errors**: Register surfaces validation/conflict messages; login uses invalid-credentials vs unexpected-failure copy

**Post-design re-check (2026-07-13)**: File-store constitution exception is **lifted** for merge — auth persists to Docker Postgres. See [research.md](./research.md).

## Project Structure

### Documentation (this feature)

```text
specs/001-web-app-pages/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── auth-api.md
│   └── ui-routes.md
└── tasks.md              # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
apps/web/src/
├── app/
│   ├── (auth)/login/page.tsx
│   ├── (auth)/register/page.tsx
│   ├── pricing/page.tsx              # signed-in upgrade UI
│   ├── dashboard/page.tsx            # AddressSearch + lookups
│   ├── compare/page.tsx              # coming soon
│   ├── report/[addressId]/page.tsx  # Back to dashboard if signed in
│   └── api/auth/[...nextauth]/route.ts
├── components/
│   ├── layout/Header.tsx             # guest vs signed-in
│   ├── layout/UserMenu.tsx
│   ├── layout/Footer.tsx             # Sign in guests only
│   ├── landing/PricingSection.tsx    # guest marketing vs signed-in upgrade
│   ├── pricing/PricingTiersGrid.tsx  # shared guest | upgrade modes
│   └── paywall/UpgradePrompt.tsx
├── lib/auth.ts
└── __tests__/

apps/api/
├── app/
│   ├── db/                    # engine/session (SQLAlchemy async)
│   ├── models/                # ORM: User, AddressLookup, SavedLookup
│   ├── api/v1/endpoints/auth.py
│   ├── api/v1/endpoints/users.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_store.py      # Protocol + PostgresUserStore
│   │   └── lookup_store.py    # Protocol + PostgresLookupStore
│   └── schemas/auth.py
├── migrations/                # Alembic (align with infra/sql/init.sql)
└── tests/                     # Postgres-backed auth/lookup tests (no FileUserStore)
```

**Structure Decision**: UI in `apps/web`; durable auth/lookups in FastAPI against Docker Postgres. Keep repository protocols so endpoints/services stay thin.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none active for storage)* | Local Docker Postgres replaces the prior TEMP JSONL exception | Re-introducing file store would block merge and leave a known debt |

**Mandatory before merge**: Delete `FileUserStore` / `FileLookupStore`, `apps/api/data/TEMP_*`, and file-store-only tests. Checklist in [research.md](./research.md).
