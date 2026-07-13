# Quickstart: Web App Pages

**Feature**: `001-web-app-pages` | **Date**: 2026-07-10 | **Updated**: 2026-07-13

Validation guide after implementation. See [contracts/auth-api.md](./contracts/auth-api.md) and [data-model.md](./data-model.md) for shapes.

## Prerequisites

- Docker Desktop running
- Stack via Compose (`npm run dev:docker` / `docker compose up`) so **`db`** (PostGIS), API, and web are up — or API/web local with `DATABASE_URL=postgresql://postgres:postgres@localhost:5433/neighborhoodiq` (Compose publishes Postgres on **5433** to avoid a local Windows Postgres on 5432)
- Env from `.env.example`: `DATABASE_URL`, `SECRET_KEY`, `AUTH_SECRET` / `NEXTAUTH_SECRET`, `NEXTAUTH_URL`, `NEXT_PUBLIC_API_URL`
- Confirm `apps/api/data/TEMP_*` are **gone** after Postgres swap (no file auth)

## Setup

1. Start Docker Desktop; run compose (or `db` + local API/web).
2. Confirm API health: `http://localhost:8000/health`.
3. Open web: `http://localhost:3000`.

## Validation scenarios

### V1 — Register and sign in (Postgres)

1. Open `/register`, submit valid name/email/password.
2. Expect signed-in header (UserMenu visible).
3. Confirm a row in Postgres:  
   `docker compose exec db psql -U postgres -d neighborhoodiq -c "SELECT email, tier FROM users ORDER BY created_at DESC LIMIT 5;"`
4. Sign out; open `/login` with same credentials; expect UserMenu again.
5. Wrong password → **“Invalid email or password”**.
6. Invalid email on register → specific validation message (not “Something went wrong”).

### V2 — Chrome and styling

1. Compare `/`, `/login`, `/pricing`, `/dashboard` header brand and fonts to splash.
2. Guest: Sign in visible in header and footer. Signed-in: UserMenu; footer has **no** Sign in.
3. From any page, Scores / AI Insights / Pricing go to `/#scores` / `/#ai` / `/#pricing`.

### V3 — Upgrade / plans (signed-in)

1. As guest: header Pricing → splash `#pricing` with register CTAs; direct `/pricing` → login redirect.
2. As signed-in: UserMenu → Plans & upgrade → `/pricing`; current plan labeled; plan buttons do nothing.
3. As signed-in on home: splash `#pricing` shows upgrade UI, not register CTAs.
4. UpgradePrompt CTA → `/pricing`.

### V4 — Dashboard

1. As signed-in user with no `saved_lookups` → address search + empty state.
2. Submit a valid address in dashboard search → report page (and saved lookup row if product writes one).
3. With seeded `saved_lookups` + `address_lookups` → list shows address; click opens `/report/{address_id}`.
4. On report as signed-in → **Back to dashboard**; as guest → link absent.
5. As guest, `/dashboard` → redirected to `/login`.

### V5 — Compare coming soon

1. Open `/compare`.
2. Expect “Feature coming soon”; **Go to dashboard** + **Back to home**.
3. No live compare UI or API errors.

## TEMP store sanity (must fail after swap)

- Grep: no `FileUserStore` / `FileLookupStore` / `TEMP_dev_` under `apps/api` (see [research.md](./research.md) checklist).

## Tests

```bash
# API (Postgres fixtures)
cd apps/api && pytest tests/test_auth_endpoints.py tests/test_user_lookups.py -q

# Web
cd apps/web && npm test
```
