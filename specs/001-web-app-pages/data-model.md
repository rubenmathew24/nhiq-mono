# Data Model: Web App Pages

**Feature**: `001-web-app-pages` | **Date**: 2026-07-10

> **Persistence note**: Entities below are logical. Physical storage for this feature is the **TEMPORARY** JSONL text files described in [research.md](./research.md). Replace with PostgreSQL tables when real auth ships; do not add parallel long-lived schemas for the file format.

## Entities

### UserAccount

| Field | Type | Rules |
|-------|------|--------|
| id | UUID string | Required; generated on register |
| email | string | Required; unique; case-insensitive match on login |
| full_name | string | Required; 1–120 chars |
| password_hash | string | Required; never store plaintext |
| tier | enum | `free` \| `buyer` \| `buyer_pro` \| `agent` \| `brokerage`; default `free` |
| created_at | ISO-8601 datetime | Required |

**Relationships**: Has many SavedLookup.

**Validation**:

- Email must look like an email (basic format check)
- Password on register: min length 8 (product default for this phase)
- Duplicate email → conflict error with “sign in instead” guidance

**State**: No workflow states beyond exists / deleted (deletion out of scope).

---

### Session (logical)

| Field | Type | Rules |
|-------|------|--------|
| user_id | UUID string | Subject of JWT / Auth.js session |
| access_token | string | Opaque to UI beyond Authorization header |
| expires_at | datetime | Align with JWT exp (design default ~7 days) |

Issued by `POST /api/v1/auth/login` (and after successful register + login). Ended by client sign-out (Auth.js).

---

### SavedLookup

| Field | Type | Rules |
|-------|------|--------|
| user_id | UUID string | Required; owner |
| address_id | string | Required; links to report route |
| address_normalized | string | Required; display label |
| looked_up_at | ISO-8601 datetime | Required; sort newest first |

**Relationships**: Belongs to UserAccount; references NeighborhoodReport by `address_id` (report payload not duplicated in lookup store).

---

### NeighborhoodReport

Existing product entity (already typed in web `types/api.ts`). Live compare (two reports) is deferred; no schema change required for this feature beyond reading via existing score API / fixtures for single-address reports.

---

### SubscriptionTier (enum on UserAccount)

| Tier | Notes (this feature) |
|------|----------------------|
| anonymous / free | Default on register; shown as current plan on upgrade UI |
| buyer+ | Seeded for future compare; not gated in UI this feature |

Upgrade page (`/pricing`) displays marketing tiers and labels the user’s current `tier` from session; plan buttons do not mutate tier. No payment entity and no tier-update API in this feature. Live compare entitlement is deferred.

## Temporary file mapping

| Entity | TEMP file | Line shape |
|--------|-----------|------------|
| UserAccount | `apps/api/data/TEMP_dev_users.jsonl` | One JSON object / line |
| SavedLookup | `apps/api/data/TEMP_dev_lookups.jsonl` | One JSON object / line |

## Future Postgres mapping (removal target)

| Entity | Intended table (design docs) |
|--------|------------------------------|
| UserAccount | `users` |
| SavedLookup | `address_lookups` (or equivalent user-scoped history) |
