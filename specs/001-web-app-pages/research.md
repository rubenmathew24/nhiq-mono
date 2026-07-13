# Research: Web App Pages

**Feature**: `001-web-app-pages` | **Date**: 2026-07-10

## Decision: Docker Compose PostgreSQL for auth & saved lookups (supersedes TEMP JSONL)

**Decision (updated 2026-07-13)**: Persist register/login/`/users/me`/saved-lookups in the **local Docker Compose** PostGIS database (`db` service). Keep `UserStore` / `LookupStore` protocols; implement `PostgresUserStore` / `PostgresLookupStore`. Web never talks to SQL.

**Rationale**: File store was a time-boxed spoof so UI could ship. Before merge to `master`, auth must use the constitution datastore (Postgres). Docker Compose is already the local DB (`DATABASE_URL`, `infra/sql/init.sql`).

**Alternatives considered**:

| Alternative | Why rejected |
|-------------|--------------|
| Keep TEMP JSONL through merge | Leaves known debt; constitution expects Postgres as system of record |
| Azure Flexible Server now | Out of scope for local pre-merge; Azure comes with deploy later |
| Host-only Postgres (non-Docker) | Extra setup; compose `db` is already wired for the monorepo |
| SQLite | Not the locked stack |

### Table mapping

| API / entity | Postgres |
|--------------|----------|
| UserAccount | `users` (`hashed_password` column ↔ app `password_hash`) |
| SavedLookup list | `saved_lookups` ⋈ `address_lookups` (`address_id` = `address_lookups.id`, label/normalized from address row, `looked_up_at` ← `saved_lookups.created_at`) |

Ensure `infra/sql/init.sql` matches design docs for columns needed by auth (e.g. `users` fields). Seed optional demo user/saved rows via SQL or a one-shot script — not JSONL.

### TEMP file store removal checklist (MUST complete before merge)

1. Add SQLAlchemy session/engine + ORM models for `users`, `address_lookups`, `saved_lookups` aligned with `infra/sql/init.sql` / `08-database-schema.md`.
2. Implement Postgres repositories; keep the same `UserStore` / `LookupStore` method signatures used by `AuthService` and users endpoints.
3. Delete `apps/api/data/TEMP_*` files and `TEMP_REMOVE_WHEN_REAL_AUTH.md`; remove file-store classes.
4. Default to database only (no `AUTH_STORE=file` flag).
5. Grep the repo for `TEMP_`, `FileUserStore`, `FileLookupStore`, `dev_users.jsonl` — zero hits remaining.
6. Replace file-store tests with Postgres fixtures (compose `db` or pytest DB); delete `test_auth_file_store.py` if file-only.
7. Update quickstart: start `db` (and redis/api/web as needed) via Docker Compose; validate register → row in `users`.
8. PR note: “Replaces temporary file auth with Docker Postgres for 001-web-app-pages.”

---

## Decision: Auth.js (Auth.js / next-auth v5) on the web

**Decision**: Add Auth.js with Credentials provider that calls FastAPI `POST /api/v1/auth/login` (and register via dedicated page → API then sign-in). Session exposes access token for `apiFetch`.

**Rationale**: Matches `docs/nhiq-design-main/02-nextjs-frontend.md`; keeps session in httpOnly cookie; aligns with constitution (browser does not own password DB).

**Alternatives considered**: Custom cookie-only Next route handlers (more bespoke); raw JWT in `localStorage` (XSS risk, rejected).

---

## Decision: Visual system reuse

**Decision**: Reuse existing CSS variables, `Header`/`Footer`, `Button`/`ButtonWithArrow`, fonts (`DM Sans` / `Space Grotesk`), and landing content modules. Extract shared pricing copy from `content/landing.ts` for `/pricing` so splash and pricing stay in sync.

**Rationale**: Spec SC-003 / FR-005 require matching splash/report styling.

**Alternatives considered**: New component library or dark slate-only auth theme from older doc snippets — rejected (would fork visual language).

---

## Decision: Compare deferred to coming-soon placeholder

**Decision (updated 2026-07-10)**: Live side-by-side compare (API tier gate, CompareResults UI, UpgradePrompt on `/compare`) is **deferred**. `/compare` is a public “Feature coming soon” page; UserMenu still links there. `UpgradePrompt` component remains for future gates. FastAPI `/api/v1/compare` stays an empty stub. Buyer demo seed may remain for future work.

**Rationale**: Live compare broke the site; placeholder keeps navigation discoverable without shipping broken UX.

**Prior decision (superseded)**: Freemium compare gating via `tier` + `GET /api/v1/compare` 402 + UpgradePrompt — deferred until a dedicated compare feature ships.

---

## Decision: Clear user-facing errors (Constitution VIII)

**Decision**: “Something went wrong” is reserved for unexpected/server/network failures. Register surfaces validation/conflict details. Login uses one “Invalid email or password” message for auth rejection (no email/password enumeration).

**Rationale**: Constitution Principle VIII (v1.1.0); avoids training users to treat validation as outages.

---

## Decision: Dashboard data source

**Decision (updated 2026-07-13)**: List lookups from Postgres `saved_lookups` joined to `address_lookups`, filtered by `user_id`. Empty set → empty dashboard. Opening a row navigates to `/report/[addressId]` where `addressId` is `address_lookups.id`. Dashboard embeds `AddressSearch` for new lookups.

**Rationale**: Same product behavior as the TEMP store, durable in Docker Postgres.

---

## Decision: `/pricing` is signed-in upgrade UI only (no billing)

**Decision (updated 2026-07-10)**: Header “Pricing” → splash `/#pricing`. Route `/pricing` is auth-required upgrade/plans page (UserMenu “Plans & upgrade”). Shows current tier from session; plan CTAs are non-functional placeholders. **No** `PATCH /users/me/tier`, Stripe, or session tier mutation in this feature. Splash `#pricing` uses the same shared `PricingTiersGrid` in `upgrade` mode when signed in so home and Plans stay aligned.

**Rationale**: Guests get marketing on splash; signed-in users get an upgrade surface without shipping fake billing that mutates entitlements.

**Alternatives considered**: Public marketing `/pricing` + TEMP tier PATCH for demo — rejected (confuses nav; fake upgrades look real).

---

## Decision: Report Back to dashboard (signed-in only)

**Decision**: `/report/[addressId]` shows a Back to dashboard link only when `auth()` has a user session. Guests do not see the control (report remains public).

**Rationale**: Dashboard is an authenticated hub; exposing the link to guests would either confuse or bounce them through login unnecessarily.

---

## Decision: Footer Sign in only for guests

**Decision**: `Footer` awaits Auth.js `auth()` and omits the Sign in link when a session exists.

**Rationale**: Avoids contradictory chrome for signed-in users.

---

## Decision: Compare coming-soon CTA preference

**Decision**: Primary CTA = `ButtonWithArrow` → `/dashboard`; secondary = text link → `/`.

**Rationale**: Signed-in users (and guests who will hit login via dashboard gate) are steered toward the product hub first.

---

## Decision: Agent context script

**Decision**: No `.specify` agent-context update script exists in this repo; skip automated agent context update. Runtime guidance remains constitution + this feature’s plan/research.

**Alternatives considered**: Hand-edit `apps/web/AGENTS.md` — optional later; not required for plan completion.
