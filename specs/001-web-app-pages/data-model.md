# Data Model: Web App Pages

**Feature**: `001-web-app-pages` | **Date**: 2026-07-10 | **Updated**: 2026-07-13

> **Persistence**: Docker Compose PostgreSQL (`db`). Entities map to tables in `infra/sql/init.sql` and `docs/nhiq-design-main/08-database-schema.md`. TEMP JSONL is removed before merge.

## Entities

### UserAccount

| Field | Type | Rules |
|-------|------|--------|
| id | UUID | Required; generated on register |
| email | string | Required; unique; case-insensitive match on login |
| full_name | string | Required; 1–120 chars |
| password_hash | string | Required; bcrypt; DB column `hashed_password` |
| tier | enum | `free` \| `buyer` \| `buyer_pro` \| `agent` \| `brokerage`; default `free` |
| created_at | timestamptz | Required |

**Relationships**: Has many SavedLookup via `saved_lookups`.

**Validation**:

- Email format check
- Password on register: min length 8
- Duplicate email → conflict with “sign in instead” guidance

---

### Session (logical)

| Field | Type | Rules |
|-------|------|--------|
| user_id | UUID string | Subject of JWT / Auth.js session |
| access_token | string | Opaque to UI beyond Authorization header |
| expires_at | datetime | Align with JWT exp (~7 days) |

Issued by `POST /api/v1/auth/login` (and after register + login). Ended by client sign-out.

---

### SavedLookup

| Field | Type | Rules |
|-------|------|--------|
| user_id | UUID | Required; owner (`saved_lookups.user_id`) |
| address_id | UUID string | Required; `address_lookups.id` (report route key) |
| address_normalized | string | Required; display from `address_lookups.address_normalized` |
| looked_up_at | timestamptz | Required; `saved_lookups.created_at`; sort newest first |

**Relationships**: Belongs to UserAccount; references `address_lookups` (and thus report by id). Creating a saved lookup may upsert an `address_lookups` row when recording a new address.

---

### NeighborhoodReport

Existing product entity. Live compare deferred; no schema change beyond reading via existing score API / fixtures.

---

### SubscriptionTier (enum on UserAccount)

| Tier | Notes (this feature) |
|------|----------------------|
| free | Default on register; current plan on upgrade UI |
| buyer+ | Seeded for future compare; not gated in UI this feature |

`/pricing` displays tiers and labels current `tier`; plan buttons do not mutate tier.

## Postgres mapping

| Entity | Table(s) |
|--------|----------|
| UserAccount | `users` |
| SavedLookup | `saved_lookups` ⋈ `address_lookups` |
| Address cache (geocode) | `address_lookups` |
