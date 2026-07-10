---
description: "Task list for Web App Pages feature implementation"
---

# Tasks: Web App Pages

**Input**: Design documents from `/specs/001-web-app-pages/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Per Constitution Principle VI — test tasks included for each runtime user story (`apps/api/tests/`, `apps/web/src/__tests__/`).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: [US1]…[US5] on user-story phase tasks only
- Exact file paths in every description

## Path Conventions

- **Web**: `apps/web/src/`
- **API**: `apps/api/app/`, tests in `apps/api/tests/`
- **TEMP store**: `apps/api/data/TEMP_*` (must be removed when real auth ships — see research.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies, env, and TEMP data scaffolding

- [x] T001 Create feature git branch `001-web-app-pages` from current mainline and confirm working tree
- [x] T002 [P] Add Auth.js (`next-auth`), `zod`, and Vitest + Testing Library deps to `apps/web/package.json`
- [x] T003 [P] Add JWT/password libs (e.g. PyJWT or python-jose, passlib[bcrypt]) to `apps/api` requirements and document env keys (`SECRET_KEY`, `NEXTAUTH_SECRET`, `NEXTAUTH_URL`, `NEXT_PUBLIC_API_URL`) in `.env.example`
- [x] T004 [P] Create `apps/api/data/TEMP_REMOVE_WHEN_REAL_AUTH.md` with removal checklist link to `specs/001-web-app-pages/research.md`
- [x] T005 [P] Add `apps/api/data/.gitignore` (ignore runtime JSONL; allow `TEMP_REMOVE_WHEN_REAL_AUTH.md` and optional seed examples) plus empty/seed `apps/api/data/TEMP_dev_users.jsonl` and `apps/api/data/TEMP_dev_lookups.jsonl`
- [x] T006 [P] Configure Vitest in `apps/web/vitest.config.ts` and `apps/web/src/__tests__/setup.ts`; add `test` script to `apps/web/package.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: TEMP file store, auth schemas/JWT, Auth.js wiring — blocks all user stories

**CRITICAL**: No user story work until this phase completes

- [x] T007 Create `UserStore` protocol + `FileUserStore` with TEMP banner comment in `apps/api/app/services/user_store.py`
- [x] T008 Create `LookupStore` protocol + `FileLookupStore` with TEMP banner in `apps/api/app/services/lookup_store.py`
- [x] T009 [P] Add Pydantic auth/user schemas in `apps/api/app/schemas/auth.py` matching `specs/001-web-app-pages/contracts/auth-api.md`
- [x] T010 [P] Implement password hash/verify + JWT create/decode helpers in `apps/api/app/core/security.py` (or extend existing core module)
- [x] T011 Implement `AuthService` (register, login, get_me) using stores in `apps/api/app/services/auth_service.py`
- [x] T012 Wire thin routes `POST /register`, `POST /login` in `apps/api/app/api/v1/endpoints/auth.py`
- [x] T013 Wire thin routes `GET /me`, `GET /me/lookups` in `apps/api/app/api/v1/endpoints/users.py` with Bearer dependency
- [x] T014 Add Auth.js config (Credentials → FastAPI login) in `apps/web/src/lib/auth.ts`
- [x] T015 Add Auth.js route handlers in `apps/web/src/app/api/auth/[...nextauth]/route.ts`
- [x] T016 Add session `SessionProvider` (or equivalent) in `apps/web/src/app/providers.tsx` and wrap in `apps/web/src/app/layout.tsx`
- [x] T017 [P] Extend web auth types in `apps/web/src/types/api.ts` (User, LoginResponse, LookupsResponse)
- [x] T018 Write API tests for file store + register/login/me in `apps/api/tests/test_auth_file_store.py` and `apps/api/tests/test_auth_endpoints.py`

**Checkpoint**: `POST /api/v1/auth/register` + `login` work against TEMP files; Auth.js can obtain a session

---

## Phase 3: User Story 1 — Sign up and sign in (Priority: P1) 🎯 MVP

**Goal**: Visitors can register and sign in with email/password; signed-in users can sign out

**Independent Test**: Complete register and login with valid/invalid credentials; confirm success and errors without dashboard/compare

### Tests for User Story 1

- [x] T019 [P] [US1] Add failing Vitest coverage for login/register form validation in `apps/web/src/__tests__/auth-forms.test.tsx`

### Implementation for User Story 1

- [x] T020 [P] [US1] Build shared auth form UI primitives (inputs, error alert) in `apps/web/src/components/auth/AuthFormFields.tsx` matching splash/report tokens
- [x] T021 [US1] Implement register page in `apps/web/src/app/(auth)/register/page.tsx` (API register → Auth.js sign-in)
- [x] T022 [US1] Implement login page in `apps/web/src/app/(auth)/login/page.tsx` (Auth.js credentials)
- [x] T023 [US1] Add auth layout shell (Header/Footer, centered card) in `apps/web/src/app/(auth)/layout.tsx` consistent with existing styling
- [x] T024 [US1] Ensure sign-out works via Auth.js `signOut` callable from a minimal control on auth success path or temporary header link until US2 UserMenu lands

**Checkpoint**: US1 independently demoable — register, login, logout, error states

---

## Phase 4: User Story 2 — Site chrome and user menu (Priority: P1)

**Goal**: Header shows guest vs signed-in actions; UserMenu exposes identity, dashboard link, sign out; styling matches splash/report

**Independent Test**: Browse home/report/login/register as guest and signed-in; verify header/UserMenu without needing dashboard data or compare

### Tests for User Story 2

- [x] T025 [P] [US2] Add Vitest for UserMenu guest vs signed-in rendering in `apps/web/src/__tests__/user-menu.test.tsx`

### Implementation for User Story 2

- [x] T026 [P] [US2] Create `UserMenu` in `apps/web/src/components/layout/UserMenu.tsx` (name/email, Dashboard, Sign out)
- [x] T027 [US2] Update `apps/web/src/components/layout/Header.tsx` for guest (Sign in / Get started) vs signed-in (UserMenu) without breaking splash absolute nav treatment
- [x] T028 [US2] Update nav targets in `apps/web/src/content/landing.ts` (and Header) so Pricing can route to `/pricing` when that page exists; keep in-page anchors on splash where appropriate
- [x] T029 [US2] Verify report page still uses shared Header in `apps/web/src/app/report/[addressId]/page.tsx` with no layout regression

**Checkpoint**: Guest and signed-in chrome consistent across `/`, `/login`, `/register`, `/report/...`

---

## Phase 5: User Story 3 — Pricing page and upgrade path (Priority: P2)

**Goal**: Dedicated `/pricing` matching splash pricing content; upgrade CTAs lead to register/sign-in

**Independent Test**: Open `/pricing` as guest/signed-in; CTAs work; no Stripe required

### Tests for User Story 3

- [x] T030 [P] [US3] Add Vitest asserting pricing tiers render from shared content in `apps/web/src/__tests__/pricing-page.test.tsx`

### Implementation for User Story 3

- [x] T031 [P] [US3] Extract/share pricing tier content for reuse in `apps/web/src/content/landing.ts` (or `apps/web/src/content/pricing.ts`)
- [x] T032 [US3] Implement pricing page in `apps/web/src/app/pricing/page.tsx` using shared content + existing Header/Footer styling
- [x] T033 [US3] Point splash `PricingSection` CTAs / Header Get started toward `/pricing` or register as appropriate in `apps/web/src/components/landing/PricingSection.tsx` and `apps/web/src/components/layout/Header.tsx`
- [x] T034 [P] [US3] Create `UpgradePrompt` in `apps/web/src/components/paywall/UpgradePrompt.tsx` with CTA to `/pricing`

**Checkpoint**: `/pricing` matches splash tiers; UpgradePrompt navigates to pricing

---

## Phase 6: User Story 4 — Dashboard of saved lookups (Priority: P2)

**Goal**: Signed-in users see saved lookups (or empty state); guests redirected to login; rows open reports

**Independent Test**: Empty vs seeded lookups; guest redirect; open report from a row

### Tests for User Story 4

- [x] T035 [P] [US4] Add API test for `GET /users/me/lookups` empty and seeded cases in `apps/api/tests/test_user_lookups.py`
- [x] T036 [P] [US4] Add Vitest for dashboard empty state UI in `apps/web/src/__tests__/dashboard.test.tsx`

### Implementation for User Story 4

- [x] T037 [US4] Ensure `FileLookupStore` list-by-user and seed example rows work via `apps/api/app/services/lookup_store.py` + `apps/api/data/TEMP_dev_lookups.jsonl`
- [x] T038 [US4] Implement dashboard page (auth-gated) in `apps/web/src/app/dashboard/page.tsx` calling `GET /api/v1/users/me/lookups` with session token
- [x] T039 [P] [US4] Add dashboard list/empty components in `apps/web/src/components/dashboard/LookupList.tsx`
- [x] T040 [US4] Redirect unauthenticated `/dashboard` access to `/login` (middleware or server check) in `apps/web/src/middleware.ts` or dashboard page server guard

**Checkpoint**: Dashboard empty/full/guest behaviors match spec US4

---

## Phase 7: User Story 5 — Compare two addresses (Priority: P3) — SUPERSEDED

> **Superseded 2026-07-10**: Live compare deferred. See Phase 9 for coming-soon placeholder + teardown. Tasks T041–T047 below are historical (completed then rolled back / replaced).

**Goal (original)**: Eligible users see side-by-side compare; free/anonymous see UpgradePrompt; incomplete selection guided

**Independent Test**: Buyer seed user compares two known ids; free user sees upgrade; one-address incomplete state

### Tests for User Story 5

- [x] T041 [P] [US5] Add API tests for compare 200 / 402 / 404 in `apps/api/tests/test_compare_endpoint.py` *(removed in Phase 9)*
- [x] T042 [P] [US5] Add Vitest for compare upgrade vs results UI in `apps/web/src/__tests__/compare-page.test.tsx` *(replaced by coming-soon test in Phase 9)*

### Implementation for User Story 5

- [x] T043 [US5] Implement compare service + thin `GET /api/v1/compare` *(reverted to empty stub in Phase 9)*
- [x] T044 [P] [US5] Seed at least one `buyer` demo user in `apps/api/data/TEMP_dev_users.jsonl` for eligible compare testing
- [x] T045 [US5] Implement compare page *(replaced by coming soon in Phase 9)*
- [x] T046 [P] [US5] Add compare results UI *(deleted in Phase 9)*
- [x] T047 [US5] Link Compare from UserMenu (and/or nav) in `apps/web/src/components/layout/UserMenu.tsx`

**Checkpoint**: US5 independently demoable with free vs buyer seeds — **no longer applicable**; use Phase 9 checkpoint

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Docs, TEMP markers, quickstart validation, cleanup

- [x] T048 [P] Run through `specs/001-web-app-pages/quickstart.md` scenarios V1–V5 and note results in PR description
- [x] T049 [P] Grep for missing TEMP banners on file-store modules; confirm `TEMP_REMOVE_WHEN_REAL_AUTH.md` lists deletion steps
- [x] T050 [P] Add brief note to `apps/web/AGENTS.md` or feature README snippet: file auth is temporary — do not extend; replace with Postgres
- [x] T051 Run full API pytest subset and web `npm test`; fix failures in touched packages
- [x] T052 Visual pass: login, register, pricing, dashboard, compare match splash/report fonts/colors/header brand

---

## Phase 9: Bugfix — Nav, Errors, Compare Coming Soon

**Purpose**: Address post-implement bugs; align with Constitution VIII and deferred compare

- [x] T053 Fix header/footer nav: `navLinks` → `/#scores`, `/#ai`; Footer Sign in → `/login`
- [x] T054 Add Constitution Principle VIII (Clear User-Facing Errors) v1.1.0; sync plan-template Constitution Check
- [x] T055 Normalize FastAPI `detail` in `apiFetch`; register validation messages; login invalid-credentials vs unexpected failure; tests
- [x] T056 Replace live compare with coming-soon page; delete CompareResults/service/compare API tests; stub `compare.py`; unprotect `/compare` in middleware
- [x] T057 Update spec/plan/tasks/contracts/research/data-model/quickstart for deferred compare + error messaging + nav
- [x] T058 Re-run web `npm test` + API pytest subset; smoke `/pricing` nav, register invalid email, `/compare`

**Checkpoint**: Pricing nav works off-home; register/login errors follow Constitution VIII; `/compare` is coming soon

---

## Phase 10: Upgrade UI, Dashboard Search, Footer Auth, Compare CTAs

**Purpose**: Signed-in upgrade page (UI only); header Pricing → splash; dashboard AddressSearch; footer Sign in guests only; compare CTA swap

- [x] T059 Header Pricing → `/#pricing`; UserMenu Plans & upgrade → `/pricing`; middleware gate `/pricing`
- [x] T060 Reshape `/pricing` as upgrade UI with current tier; plan CTAs non-functional (no tier API)
- [x] T061 Embed `AddressSearch` on dashboard; empty-state copy; remove AddressSearch debug fetches
- [x] T062 Footer: hide Sign in when authenticated via `auth()`
- [x] T063 Compare coming soon: Dashboard primary `ButtonWithArrow`; Home secondary link; update Vitest
- [x] T064 Update spec/plan/tasks/contracts/research/data-model/quickstart for Phase 10
- [x] T065 Re-run web `npm test` + API pytest subset; smoke guest/signed-in pricing, dashboard search, footer, compare CTAs

**Checkpoint**: Guests use splash pricing; signed-in upgrade is UI-only; dashboard search works; footer/compare CTAs match plan

---

## Phase 11: Splash Upgrade Parity + Report Dashboard Link

**Purpose**: Signed-in splash `#pricing` matches upgrade UI; report Back to dashboard for signed-in users only

- [x] T066 Extract shared `PricingTiersGrid` (`guest` | `upgrade`); splash `PricingSection` uses `auth()` for upgrade mode when signed in
- [x] T067 Report page: Back to dashboard link only when `auth()` session exists (success + error states)
- [x] T068 Update spec/plan/tasks (and related contracts/quickstart) for splash upgrade parity + report dashboard link

**Checkpoint**: Signed-in home `#pricing` matches Plans & upgrade; guests see no report dashboard link

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: After Foundational — MVP
- **US2 (Phase 4)**: After Foundational; ideally after US1 so sign-out lives in UserMenu (can start Header shell in parallel with US1 pages)
- **US3 (Phase 5)**: After Foundational; UpgradePrompt available for future gates
- **US4 (Phase 6)**: After Foundational + US2 (dashboard link in UserMenu)
- **US5 (Phase 7)**: **Superseded** by Phase 9 coming-soon placeholder
- **Polish (Phase 8)**: After desired stories complete
- **Phase 9**: After Phase 8; bugfix + spec sync
- **Phase 10**: After Phase 9; upgrade UI + dashboard search + footer/compare polish
- **Phase 11**: After Phase 10; splash upgrade parity + report dashboard link

### User Story Dependencies

- **US1 (P1)**: No dependency on US2–US5
- **US2 (P1)**: Needs Auth.js session from Foundational; enhanced by US1 pages existing
- **US3 (P2)**: Independent of US4/US5 data
- **US4 (P2)**: Needs auth + lookups API from Foundational; UserMenu link from US2
- **US5 (P3)**: Coming-soon placeholder only (live compare deferred)

### Within Each User Story

- Tests alongside implementation (Principle VI)
- Services before thin API routes
- API before web pages that call it
- Story complete before next priority when staffing is serial

### Parallel Opportunities

- T002–T006 (Setup) in parallel
- T009–T010 in parallel after T007–T008 started
- T019 with T020; T025 with T026; T030 with T031; T035–T036 with T037
- Phase 9 T053–T055 can proceed in parallel with T056 after docs intent is clear

---

## Parallel Example: User Story 1

```bash
# Tests + form primitives together:
Task: "T019 Vitest auth forms in apps/web/src/__tests__/auth-forms.test.tsx"
Task: "T020 AuthFormFields in apps/web/src/components/auth/AuthFormFields.tsx"

# Then pages sequentially:
Task: "T021 register/page.tsx"
Task: "T022 login/page.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 Setup
2. Complete Phase 2 Foundational (TEMP store + Auth.js)
3. Complete Phase 3 US1 (login/register)
4. **STOP and VALIDATE** per quickstart V1
5. Demo auth before chrome/pricing/dashboard/compare

### Incremental Delivery

1. Setup + Foundational → auth API works
2. US1 → register/login MVP
3. US2 → UserMenu chrome
4. US3 → pricing + UpgradePrompt
5. US4 → dashboard
6. US5 → compare **coming soon** (live compare deferred)
7. Polish → quickstart + TEMP removal docs
8. Phase 9 → nav/errors/compare placeholder fixes
9. Phase 10 → upgrade UI-only, dashboard search, footer auth, compare CTAs
10. Phase 11 → splash upgrade parity, report Back to dashboard (signed-in only)

### Parallel Team Strategy

1. Together: Setup + Foundational
2. Then: Dev A = US1→US2; Dev B = US3; Dev C = US4 API seeds

---

## Notes

- Every TEMP file-store touch MUST keep the deletion banner (research.md checklist)
- Do not put user text files under `apps/web`
- Keep business logic in FastAPI services; Next.js stays thin (Principle II)
- User-facing errors follow Constitution VIII
- Suggested MVP scope: **Phase 1–3 (US1 only)**

---

## Phase 12: Convergence

- [x] T069 Honor `callbackUrl` after login (and align dashboard server redirect to include `callbackUrl`) per Edge case session return / FR-008 (partial)
- [x] T070 Make seeded dashboard lookups open a working report (replace `demo-address-001` with resolvable score data or seed Redis/fixture) per US4/AC3 (partial)
- [x] T071 Add a clear dashboard loading state (`loading.tsx` and/or Suspense) per US4 loading states (missing)
- [x] T072 Remove leftover `_agent_log` / `debug-9a6fa9.log` instrumentation from `apps/api/app/api/v1/endpoints/lookup.py` and `apps/api/app/services/geocoding.py` per unrequested debug leftover (unrequested)
- [x] T073 Add Vitest coverage for signed-in splash/upgrade tier mode and report Back to dashboard visibility per Constitution VI / FR-006 / FR-016 (partial)
