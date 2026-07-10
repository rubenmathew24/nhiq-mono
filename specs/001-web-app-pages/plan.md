# Implementation Plan: Web App Pages

**Branch**: `001-web-app-pages` (feature dir; create/switch git branch at implement time) | **Date**: 2026-07-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-web-app-pages/spec.md` plus plan constraint: no user database yet — temporary text-file user/lookup store; remove when real backend auth ships.

## Summary

Ship the missing web surfaces (login, register, user menu, **signed-in upgrade/plans page**, dashboard with address search, compare **coming-soon placeholder**) while matching existing splash/report styling. Auth and saved-lookup APIs are implemented in FastAPI behind `/api/v1/*` using a **temporary file-backed store** (no Postgres users table yet). The web app stays thin: Auth.js credentials + `apiFetch`, shared Header/UserMenu chrome, and pages that reuse current design tokens. `/pricing` is auth-gated **UI-only** upgrade (no billing / no tier PATCH). Header Pricing → splash `/#pricing`; splash `#pricing` switches to the same upgrade UI when signed in (shared `PricingTiersGrid`). Report pages show **Back to dashboard** only for signed-in users. File store is isolated behind a repository interface and marked for mandatory removal when Postgres user auth is implemented. Live compare is deferred.

## Technical Context

**Language/Version**: TypeScript (Next.js App Router in `apps/web`, currently Next 16.x in repo) + Python 3.12 (FastAPI in `apps/api`)

**Primary Dependencies**: Next.js, Tailwind, Auth.js (next-auth v5 — to add), zod (to add for auth responses), existing `apiFetch`; FastAPI, Pydantic, JWT issuance (python-jose/PyJWT + passlib/bcrypt as in design docs)

**Storage**: **TEMPORARY** newline-delimited text/JSONL files under `apps/api/data/` for users and saved lookups (gitignored real data; committed example/seed). **Target**: PostgreSQL `users` / `address_lookups` — not used for auth in this feature. Score/report data continues via existing score API / mocks.

**Testing**: Vitest + Testing Library for web (`apps/web/src/__tests__/`); pytest for API auth/file-store (`apps/api/tests/`)

**Target Platform**: Local Docker Compose / browser (desktop + mobile web)

**Project Type**: Monorepo web application (Next.js frontend + FastAPI backend)

**Performance Goals**: Auth form submit feedback under 2s locally; page navigations feel instant; no government API calls on these pages

**Constraints**: Match existing visual system; no Stripe; email/password only; file store is **dev/demo only** and MUST be deleted when real user DB lands; secrets not committed (file may hold demo hashes only)

**Scale/Scope**: Single-developer local demo scale (file store is not multi-instance safe); pages: `/login`, `/register`, `/pricing` (signed-in upgrade UI), `/dashboard` (search + lookups), `/compare` (coming soon) + Header/UserMenu/Footer auth; splash `#pricing` auth-aware; report Back to dashboard when signed in; splash + report preserved

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodIQ Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**: Next.js + FastAPI + existing monorepo layout; no alternate stack
- [x] **II. Thin Client, Fat API**: Auth/register/login/lookups live in FastAPI services; web uses `apiFetch` + Auth.js session chrome only *(file store is temporary backend adapter — see Complexity Tracking)*
- [x] **III. Precomputed Data Path**: New pages do not ingest government data or compute scores; dashboard consumes existing score/report contracts or fixtures; live compare deferred
- [x] **IV. API Contracts & Versioning**: `/api/v1/auth/*`, `/api/v1/users/me`, lookups list under v1; Pydantic request/response models
- [x] **V. Security & Secrets**: Passwords hashed in file store; JWT secret from env; data files gitignored; UI gates are UX — API still checks session *(file store is not production-grade — Complexity Tracking)*
- [x] **VI. Test Alongside Features**: Auth API + file-store tests; web tests for auth forms, UserMenu states, pricing/dashboard empty states, compare coming soon
- [x] **VII. Observability & Graceful Degradation**: Log auth failures at WARNING; missing lookup file → empty dashboard; no new streaming infra
- [x] **VIII. Clear User-Facing Errors**: Register surfaces validation/conflict messages; login uses invalid-credentials vs unexpected-failure copy; “Something went wrong” reserved for unexpected failures

**Post-design re-check**: Same as above. Temporary file adapter is an explicit, time-boxed constitution exception documented in Complexity Tracking and [research.md](./research.md).

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
├── data/                      # TEMPORARY — gitignore contents except .gitkeep / example
│   ├── TEMP_REMOVE_WHEN_REAL_AUTH.md
│   ├── TEMP_dev_users.jsonl   # example seed only in repo
│   └── TEMP_dev_lookups.jsonl
├── app/
│   ├── api/v1/endpoints/auth.py
│   ├── api/v1/endpoints/users.py
│   ├── services/
│   │   ├── auth_service.py
│   │   └── user_store.py      # Protocol + FileUserStore (TEMPORARY)
│   └── schemas/auth.py
└── tests/test_auth_file_store.py
```

**Structure Decision**: UI in `apps/web`; temporary persistence and JWT auth in `apps/api` so the client contract matches the future Postgres-backed API. Do not put the user text file in the Next.js app.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **V / production secrets & durable store**: file-backed users instead of Postgres + Key Vault | No user DB yet; need working login/signup/dashboard UX now | Skipping auth UI blocks the feature; putting users only in browser localStorage violates Thin Client and cannot be shared with API JWT flow |
| **Horizontal scale**: single-process file I/O | Demo/local only | Redis/Postgres would be the real fix — deferred until user table exists |

**Mandatory removal**: When Postgres `users` (and lookups) are implemented, delete `FileUserStore`, `apps/api/data/TEMP_*`, and switch services to ORM repositories. Tracked in [research.md](./research.md) § Temporary auth store removal checklist.
