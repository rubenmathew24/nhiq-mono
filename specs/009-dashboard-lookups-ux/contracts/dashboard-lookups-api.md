# Contract: Dashboard lookups API

Base: `/api/v1` · Auth: Bearer required for all routes below unless noted.

## Enriched list item

```json
{
  "user_id": "uuid",
  "address_id": "uuid",
  "address_normalized": "string",
  "looked_up_at": "ISO-8601",
  "last_activity_at": "ISO-8601",
  "is_favorite": false,
  "overall_score": 72.3
}
```

- `overall_score`: number when a score row exists for the address `geoid` + active vintage; otherwise `null`.
- `looked_up_at`: first saved time (`created_at`); keep for display compatibility.
- Dual listing is **client-derived**: Favorites = `is_favorite`; Recent = all items sorted by `last_activity_at` desc.

## `GET /users/me/lookups`

**Response** `200`:

```json
{ "items": [ /* SavedLookup enriched */ ] }
```

**Behavior**:
- Ensures one-time duplicate merge for the user if not yet done.
- Ordered by `last_activity_at` desc (or unordered + client sorts — prefer server sort by activity).

## `PATCH /users/me/lookups/{address_id}`

Body:

```json
{ "is_favorite": true }
```

**Response** `200`: enriched item  
**Errors**: `404` if no saved row for this user/address.

## `DELETE /users/me/lookups/{address_id}`

**Response** `204`  
**Errors**: `404` if not owned / missing.  
Does not delete `address_lookups` or scores.

## `POST /users/me/lookups/{address_id}/touch`

Bumps `last_activity_at` for the user’s saved row.

**Response** `200`: enriched item  
**Errors**: `404` if not saved for user.

## Lookup attach behavior (existing `GET /lookup`)

When authenticated:
- Reuse existing `address_lookups` for same place (`geoid` preferred).
- Upsert `saved_lookups` for that `address_lookup_id` and set `last_activity_at=now()` (no second row for same place).

## Error shape

Standard FastAPI `{ "detail": "..." }` plus optional `code` when useful (`LOOKUP_NOT_SAVED`, etc.).
