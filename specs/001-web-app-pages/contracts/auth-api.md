# Contract: Auth & user API (`/api/v1`)

**Feature**: `001-web-app-pages` | **Date**: 2026-07-10

Backing store for this phase: **TEMPORARY** file repository ([research.md](../research.md)). Request/response shapes MUST remain valid when swapped to Postgres.

## `POST /api/v1/auth/register`

**Body**:

```json
{
  "email": "string",
  "password": "string",
  "full_name": "string"
}
```

**Responses**:

| Status | Body | When |
|--------|------|------|
| 201 | `{ "id", "email", "full_name", "tier" }` | Created |
| 409 | `{ "detail", "code": "EMAIL_EXISTS" }` | Duplicate email |
| 422 | validation error | Invalid payload |

## `POST /api/v1/auth/login`

**Body**:

```json
{
  "email": "string",
  "password": "string"
}
```

**Responses**:

| Status | Body | When |
|--------|------|------|
| 200 | `{ "access_token", "token_type": "bearer", "user": { "id", "email", "full_name", "tier" } }` | OK |
| 401 | `{ "detail", "code": "INVALID_CREDENTIALS" }` | Bad email/password (single message) |

## `GET /api/v1/users/me`

**Auth**: `Authorization: Bearer <access_token>`

**Responses**:

| Status | Body | When |
|--------|------|------|
| 200 | `{ "id", "email", "full_name", "tier" }` | OK |
| 401 | `{ "detail", "code": "UNAUTHORIZED" }` | Missing/invalid token |

## `GET /api/v1/users/me/lookups`

**Auth**: Bearer required

**Responses**:

| Status | Body | When |
|--------|------|------|
| 200 | `{ "items": [ { "address_id", "address_normalized", "looked_up_at" } ] }` | OK (may be empty list) |
| 401 | unauthorized | |

## `GET /api/v1/compare` — **DEFERRED**

Live compare is **out of scope** for this feature. The FastAPI router may keep an empty stub under `/api/v1/compare` for future work. Do not implement tier-gated side-by-side responses in this feature; the web `/compare` route is a coming-soon page only.

~~Previous contract (deferred): `GET /api/v1/compare?a=&b=` with 200 / 402 / 401 / 404.~~

