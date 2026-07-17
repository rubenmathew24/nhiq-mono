# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodInsight Constitution v1.1.0)*

- [ ] **I. Locked Stack & Monorepo**: Plan stays within Next.js 14 / FastAPI
      (Python 3.12) / PostgreSQL+PostGIS / Redis / Azure Container Apps /
      GitHub Actions / Claude; code lands under `apps/`, `workers/`,
      `packages/`, `infra/`, or `docker/` — no alternate stack proposals
- [ ] **II. Thin Client, Fat API**: Business logic, freemium gates, geocoding
      orchestration, Claude, and DB access are FastAPI `services/` (not route
      handlers, not Next.js); web uses typed `apiFetch`; only Mapbox Places
      autocomplete may call an external API from the browser
- [ ] **III. Precomputed Data Path**: User requests do not fetch government
      APIs or compute scores inline; ingestion → scoring worker →
      `neighborhood_scores`; Redis is cache-aside (invalidate on write)
- [ ] **IV. API Contracts & Versioning**: Public routes under `/api/v1/`;
      breaking changes add a new version prefix; Pydantic/zod validation;
      tier/limit enforcement server-side (`402` / `429` as appropriate)
- [ ] **V. Security & Secrets**: No secrets in code/images; prod via Key Vault;
      parameterized DB access; frontend gates are UX only
- [ ] **VI. Test Alongside Features**: Tests planned with the feature
      (`apps/api/tests/`, `apps/web/src/__tests__/`); contract/auth/scoring/
      ingestion paths covered when touched
- [ ] **VII. Observability & Graceful Degradation**: Structured logging;
      Redis/Claude failures degrade without blocking core scores; no
      streaming infra unless Complexity Tracking justifies it
- [ ] **VIII. Clear User-Facing Errors**: User-correctable failures get
      specific messages; “Something went wrong” reserved for unexpected
      failures; login uses one invalid-credentials message (no email/password
      enumeration); create flows surface validation/conflict details

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/
├── web/                 # Next.js 14 (App Router, TypeScript, Tailwind)
│   └── src/
│       ├── app/
│       ├── components/
│       ├── lib/         # apiFetch, utils
│       └── __tests__/
└── api/                 # FastAPI (Python 3.12)
    ├── app/
    │   ├── api/v1/
    │   ├── services/
    │   ├── models/
    │   └── core/
    └── tests/
workers/
├── ingest/              # Per-source scheduled ingestion
└── scoring/             # Score computation → neighborhood_scores
packages/
└── shared-types/        # Shared TypeScript types (when needed)
docker/
infra/
└── bicep/
```

**Structure Decision**: NeighborhoodInsight monorepo — place feature code under
`apps/web`, `apps/api`, and/or `workers/` per the constitution; do not
introduce a parallel top-level app layout.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
