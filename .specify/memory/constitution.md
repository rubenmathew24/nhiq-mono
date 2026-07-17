<!--
Sync Impact Report
- Version change: 1.0.0 → 1.1.0
- Modified principles: none redefined
- Added principles:
  VIII. Clear User-Facing Errors
- Added sections: none
- Removed sections: none
- Templates requiring updates:
  - .specify/templates/plan-template.md — ✅ updated (Constitution Check gate VIII)
  - .specify/templates/tasks-template.md — no change needed
  - .specify/templates/spec-template.md — no change needed
- Follow-up TODOs: none
-->

# NeighborhoodInsight Constitution

## Core Principles

### I. Locked Stack & Monorepo

NeighborhoodInsight is a single Git monorepo. Application code lives under
`apps/`, batch jobs under `workers/`, shared packages under `packages/`,
Azure IaC under `infra/`, and Docker build contexts under `docker/`.

The locked stack MUST NOT be replaced without an explicit constitution
amendment and design-doc update:

- Next.js 14 (App Router, TypeScript, Tailwind) for web
- FastAPI on Python 3.12 for the API and all business logic
- PostgreSQL 16 + PostGIS as the system of record
- Redis for cache, rate limits, and lookup counters (not durable state)
- Azure Container Apps, ACR, Front Door + WAF, Blob Storage, Key Vault
- GitHub Actions for CI/CD
- Claude API (`claude-sonnet-4-20250514`) for narratives and AI copy

Do not propose alternate frameworks, clouds, or datastores unless asked.
Rationale: locked decisions in `docs/nhiq-design-main/00-project-overview.md`
keep agents and humans aligned during build-out.

### II. Thin Client, Fat API

All business logic MUST live in FastAPI service modules (`apps/api` →
`services/`). Route handlers MUST stay thin: validate, call a service,
return a response. Next.js MUST NOT compute scores, enforce billing,
call government APIs, call Claude, or access the database.

The web app talks to the product through FastAPI (`/api/v1/*`) via a typed
`apiFetch` wrapper. Server Components are the default; `"use client"` only
when interactivity requires it. Mapbox Places autocomplete from the browser
is the only allowed client-side external API call. Mapbox Geocoding,
Census geocoding, Claude, and all government data access MUST run
server-side (API or workers).

Rationale: freemium gates and secrets cannot be trusted in the client;
centralizing logic keeps scoring and narratives consistent for web and
future B2B/API consumers.

### III. Precomputed Data Path

User-facing requests MUST NOT fetch raw government APIs or compute
neighborhood scores inline. Government data is ingested on a schedule by
workers, normalized into PostgreSQL, then scored by the scoring worker into
`neighborhood_scores`. The API serves precomputed scores from PostgreSQL
and Redis.

Cache-aside rules:

- Redis is cache-only; PostgreSQL is truth
- Workers write PostgreSQL and invalidate Redis keys; they MUST NOT treat
  Redis as a write-through store of record
- Score computation is asynchronous; clients may poll when status is
  `computing`

Rationale: government sources are batch-oriented; precomputation keeps
lookup latency predictable and isolates upstream outages from users.

### IV. API Contracts & Versioning

Public API routes MUST be prefixed `/api/v1/`. Breaking changes MUST add
`/api/v2/` (or later) and MUST NOT mutate existing v1 behavior. Responses
are JSON. Errors MUST use
`{"detail": "<human message>", "code": "<machine code>"}` with standard
HTTP status codes (including `402` for tier/limit gates and `429` for rate
limits).

All request and response bodies MUST be modeled with Pydantic (API) and
validated with zod on the web where responses are consumed. Freemium and
tier enforcement MUST run in FastAPI dependencies/middleware — never as
the sole check in the frontend.

Rationale: stable contracts protect web, B2B API keys, and future
extensions (browser overlay) from silent breakage.

### V. Security & Secrets

Secrets MUST NOT be committed, baked into Docker images, or hardcoded.
Local development uses gitignored `.env` (from `.env.example`); production
secrets MUST come from Azure Key Vault at runtime. PostgreSQL and Redis
MUST NOT be exposed on the public internet in production.

Inputs MUST be validated before business logic. Database access MUST use
parameterized queries / ORM bindings. Passwords MUST be hashed with bcrypt.
CORS MUST use an explicit allowlist. Frontend upgrade prompts are UX only;
authorization decisions remain on the server.

Rationale: credential stuffing, scraping, and secret leakage are the
primary threats at current scale; defense belongs at the API and network
edge (Front Door + WAF).

### VI. Test Alongside Features

Tests MUST be written alongside features, not deferred to a later phase.
Backend tests live under `apps/api/tests/` (pytest + pytest-asyncio).
Frontend tests live under `apps/web/src/__tests__/` (Vitest). The relevant
suite MUST pass before merging to `dev`. Promotion to `master` (prod)
MUST keep the same bar.

When a change touches API contracts, auth/tier gates, scoring, or
ingestion, tests MUST cover those paths (contract/integration as
appropriate). Ingestion loads MUST be idempotent (`ON CONFLICT` / upsert)
and scoring MUST remain reproducible for a given data vintage.

Rationale: `docs/nhiq-design-main/09-testing.md` treats tests as part of
delivery; CI on `dev`/`master` is the quality gate for deploy.

### VII. Observability & Graceful Degradation

Services MUST emit structured JSON logs to stdout (captured by Azure
Monitor). Prefer simplicity: scheduled batch workers over streaming
infrastructure until scale justifies the cost.

Degradation rules:

- Redis failure: fall through to PostgreSQL; log WARNING
- Claude failure: return scores without narrative; narrative is
  non-blocking
- Ingestion failure: keep serving cached/prior scores; alert on missed
  schedules

Rationale: users need scores even when AI or cache layers fail; batch
ingestion matches source freshness without Kafka-class complexity.

### VIII. Clear User-Facing Errors

User-visible error copy MUST distinguish **user-correctable** failures from
**unexpected system** failures.

- Prefer specific, actionable messages for validation, conflicts (e.g.
  duplicate email), and auth rejection as a class (“Invalid email or
  password”).
- Reserve vague copy such as “Something went wrong. Please try again.”
  for unexpected failures only (5xx, network errors, parse failures,
  unknown errors) — never for normal validation or expected auth rejection.
- Sign-in MUST NOT enumerate “email not found” vs “wrong password”; use one
  invalid-credentials message for 401-class auth failures.
- Sign-up and other create flows SHOULD surface what is wrong (invalid
  email, weak password, duplicate account) when the client or API knows.

Rationale: “Something went wrong” reads as a server outage; conflating it
with bad input trains users to ignore real failures and hides how to fix
their request.

## Architecture Constraints

Repository layout MUST follow the monorepo map in
`docs/nhiq-design-main/00-project-overview.md` (`apps/web`, `apps/api`,
`workers/ingest/*`, `workers/scoring`, `packages/`, `docker/`, `infra/bicep`).

URL routing:

- `/*` → Next.js
- `/api/v1/*` → FastAPI
- Internal service-to-service traffic uses the Docker/Azure network, not
  the public internet

Product score contract (five dimensions + composite): Healthcare Access,
Safety & Environment, Education & Amenities, Economic Health, and Overall
composite. Default weights (healthcare 25%, safety 25%, education 20%,
environment 15%, economic 15%) and percentile-based normalization are
product contracts — change them only with an explicit product decision and
doc update.

Redis key patterns and TTLs (score 24h, narrative 6h, geocode 7d, lookup
and rate-limit counters) are defined in
`docs/nhiq-design-main/10-system-design.md` and MUST stay consistent across
services.

Environment variable ownership (e.g. `DATABASE_URL`, `REDIS_URL`,
`ANTHROPIC_API_KEY`, `MAPBOX_TOKEN`, `NEXT_PUBLIC_API_URL`) MUST match the
overview table; new secrets require `.env.example` updates without
committing real values.

## Development Workflow

- Branch model (this repo):
  - `master` — production; CI/CD deploys from here
  - `dev` — integration / staging; spin up to test before prod
  - Spec Kit feature branches (`NNN-short-name`) — created from **`dev`**,
    merged back to **`dev`** via PR; promote `dev` → `master` for release
- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, …)
- Integration: open feature PRs to `dev`; do not push directly to `master`
  (or to `dev` except intentional integration merges). Spec Kit base branch
  is configured in `.specify/init-options.json` as `feature_base_branch`
- Python: type hints everywhere; `ruff` + `black`; async I/O in handlers
- TypeScript: `"strict": true`; Tailwind only (no CSS modules /
  styled-components for app UI)
- Schema: Alembic migrations for all PostgreSQL changes — never edit
  production columns in place
- Runtime guidance for agents and humans:
  `docs/nhiq-design-main/00-project-overview.md` and
  `docs/nhiq-design-main/10-system-design.md`, then numbered playbooks
  `01`–`09` for implementation detail

## Governance

This constitution supersedes ad-hoc practice when they conflict. If
implementation guidance in `docs/nhiq-design-main/` disagrees with this
file, either amend the constitution or update the design docs in the same
change set — do not leave silent drift.

Amendments MUST:

1. Document the change and rationale
2. Bump **Version** using semantic versioning:
   - MAJOR: remove or redefine a principle incompatibly
   - MINOR: add a principle/section or materially expand guidance
   - PATCH: clarifications, wording, non-semantic refinements
3. Set **Last Amended** to the amendment date (ISO `YYYY-MM-DD`)
4. Update dependent Speckit templates (especially plan Constitution Check
   and tasks path/test guidance) in the same PR when gates change

Pull requests and `/speckit-plan` outputs MUST pass the Constitution Check
gates before Phase 0 research proceeds. Complexity that violates a
principle MUST be recorded in the plan's Complexity Tracking table with a
simpler alternative rejected for a concrete reason.

**Version**: 1.2.0 | **Ratified**: 2026-07-09 | **Last Amended**: 2026-07-13
