# Quickstart: Web App Pages

**Feature**: `001-web-app-pages` | **Date**: 2026-07-10

Validation guide after implementation. See [contracts/auth-api.md](./contracts/auth-api.md) and [data-model.md](./data-model.md) for shapes.

## Prerequisites

- Docker Compose (or local) API + web running per repo README / compose file
- Env: `SECRET_KEY` (or JWT secret), `AUTH_SECRET` / `NEXTAUTH_SECRET`, `NEXTAUTH_URL`, `NEXT_PUBLIC_API_URL`
- Confirm `apps/api/data/TEMP_REMOVE_WHEN_REAL_AUTH.md` exists (marks temporary store)

## Setup

1. Start stack (`docker compose up` or equivalent).
2. Ensure TEMP user/lookup files exist (seed example user optional).
3. Open web app (typically `http://localhost:3000`).

## Validation scenarios

### V1 — Register and sign in

1. Open `/register`, submit valid name/email/password.
2. Expect signed-in header (UserMenu visible).
3. Sign out; open `/login` with same credentials; expect UserMenu again.
4. Wrong password → **“Invalid email or password”** (not “Something went wrong”).
5. Invalid email on register (e.g. `testing@t`) → specific validation message (not “Something went wrong”).

### V2 — Chrome and styling

1. Compare `/`, `/login`, `/pricing`, `/dashboard` header brand and fonts to splash.
2. Guest: Sign in visible in header and footer. Signed-in: UserMenu; footer has **no** Sign in.
3. From any page, Scores / AI Insights / Pricing go to `/#scores` / `/#ai` / `/#pricing`.

### V3 — Upgrade / plans (signed-in)

1. As guest: header Pricing → splash `#pricing` with register CTAs; direct `/pricing` → login redirect.
2. As signed-in: UserMenu → Plans & upgrade → `/pricing`; current plan labeled; plan buttons do nothing.
3. As signed-in on home: splash `#pricing` shows the same upgrade UI (current plan + Coming soon), not register CTAs.
4. UpgradePrompt CTA → `/pricing`.

### V4 — Dashboard

1. As signed-in user with no lookups → address search bar + empty state pointing at that search.
2. Submit a valid address in dashboard search → report page.
3. With seeded lookup row → list shows address; click opens `/report/{address_id}`.
4. On report as signed-in → **Back to dashboard** visible and works; as guest → link absent.
5. As guest, `/dashboard` → redirected to `/login` (or equivalent).

### V5 — Compare coming soon

1. Open `/compare` (guest or signed-in, including UserMenu link).
2. Expect “Feature coming soon”; primary **Go to dashboard** (arrow button); secondary **Back to home**.
3. No live compare UI or API errors.

## Temporary store sanity

- After register, a new line appears in `TEMP_dev_users.jsonl` (local only; do not commit secrets).
- Grep reminder before merge to main when real auth exists: no `FileUserStore` / `TEMP_dev_` left (see [research.md](./research.md) removal checklist).

## Tests (once implemented)

```bash
# API
cd apps/api && pytest tests/test_auth_file_store.py tests/test_auth_endpoints.py -q

# Web
cd apps/web && npm test
```
