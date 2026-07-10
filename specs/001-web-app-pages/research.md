# Research: Web App Pages

**Feature**: `001-web-app-pages` | **Date**: 2026-07-10

## Decision: Temporary file-backed user store (API-side)

**Decision**: Implement register/login/`/users/me`/saved-lookups against newline-delimited JSON text files under `apps/api/data/TEMP_*.jsonl`, accessed only through a `UserStore` / `LookupStore` protocol in FastAPI services. Web never reads these files.

**Rationale**: User confirmed there is no user database yet and asked to spoof with a text-file lookup. Keeping the spoof behind FastAPI preserves Thin Client / Fat API and keeps `/api/v1` contracts stable for the real backend swap.

**Alternatives considered**:

| Alternative | Why rejected |
|-------------|--------------|
| Browser `localStorage` only | Violates constitution (client as source of truth); no shared JWT with API |
| Skip auth until Postgres | Blocks login/signup/user menu/dashboard acceptance criteria |
| SQLite “temporary” DB | Heavier than requested; still a second persistence story to delete |
| Hardcoded single demo user | Cannot exercise register or multi-user dashboard empty/full states |

### File format (illustrative)

`TEMP_dev_users.jsonl` — one JSON object per line:

```json
{"id":"uuid","email":"demo@example.com","full_name":"Demo User","password_hash":"...","tier":"free","created_at":"2026-07-10T00:00:00Z"}
```

`TEMP_dev_lookups.jsonl`:

```json
{"user_id":"uuid","address_id":"…","address_normalized":"…","looked_up_at":"…"}
```

### Temporary auth store removal checklist

**MUST complete when real backend user tables ship:**

1. Implement SQLAlchemy models + Alembic migrations for `users` and `address_lookups` (per design schema docs).
2. Replace `FileUserStore` / `FileLookupStore` with Postgres repositories; keep the same service method signatures.
3. Delete `apps/api/data/TEMP_*` files and `TEMP_REMOVE_WHEN_REAL_AUTH.md`.
4. Remove any `AUTH_STORE=file` (or equivalent) env flag; default to database only.
5. Grep the repo for `TEMP_`, `FileUserStore`, `FileLookupStore`, `dev_users.jsonl` — zero hits remaining.
6. Update tests to use DB fixtures; delete file-store-specific tests.
7. Note in the auth PR description: “Removes temporary file auth spoof from 001-web-app-pages.”

Until then, every file-store module MUST start with a comment:

```text
TEMPORARY: File-backed auth/lookups for UI development only.
DELETE when Postgres users/address_lookups are implemented.
See specs/001-web-app-pages/research.md removal checklist.
```

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

**Decision**: List lookups from temporary lookup file filtered by `user_id`. Seed 0–2 example rows for demo user; empty state otherwise. Opening a row navigates to existing `/report/[addressId]`. Dashboard embeds the same `AddressSearch` component as splash so users can start a new lookup without leaving the page.

**Rationale**: No `address_lookups` table yet; same removal path as users file. On-page search matches product expectation that dashboard is the hub for lookups.

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
