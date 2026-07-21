# Data Model: 009-dashboard-lookups-ux

## Entities

### AddressLookup (`address_lookups`) — existing

Unchanged columns. **Behavior change**: reuse an existing row when recording a lookup for the same place (`geoid` match preferred; else exact `address_normalized`), bumping `last_looked_up_at` / `lookup_count` instead of always inserting.

### SavedLookup (`saved_lookups`) — extended

| Field | Type | Notes |
|-------|------|--------|
| id | UUID PK | existing |
| user_id | UUID FK → users | existing |
| address_lookup_id | UUID FK → address_lookups | existing; unique with user_id |
| label | text | existing |
| notes | text | existing |
| created_at | timestamptz | existing (first save) |
| **is_favorite** | boolean NOT NULL DEFAULT false | **new** |
| **last_activity_at** | timestamptz NOT NULL | **new**; default `now()`; bump on search + report open |

**Uniqueness**: Keep `UNIQUE(user_id, address_lookup_id)`. Application-level uniqueness of “one place per user” enforced by reusing `address_lookup_id` for the same geoid/normalized address.

### NeighborhoodScore (`neighborhood_scores`) — read-only join

Used only to populate `overall_score` on list responses via `geoid` + active `SCORE_DATA_VINTAGE`.

### Optional: UserLookupMergeState

Prefer a cheap approach: boolean `lookups_deduped_at` on `users` **or** idempotent merge every list (OK at small N). Plan default: **`users.lookups_deduped_at`** nullable timestamptz — set after successful merge so list stays O(n).

## Validation rules

- Favorite/unfavorite/delete/touch: caller must own the `saved_lookups` row (404 if not found for user).
- Delete removes `saved_lookups` only.
- Merge: survivor keeps max activity; `is_favorite = OR(group)`; orphaned duplicate saved rows deleted.

## State transitions

```text
[new lookup for user]
  → find/reuse AddressLookup by geoid|normalized
  → upsert SavedLookup (set last_activity_at=now)
  → if first time: is_favorite=false

[favorite]
  → is_favorite=true

[unfavorite]
  → is_favorite=false

[touch / re-search]
  → last_activity_at=now

[delete + confirm]
  → delete SavedLookup row
```

## Migration notes

- Add columns with defaults so existing rows get `is_favorite=false` and `last_activity_at=created_at`.
- Backfill `last_activity_at` from `created_at` where null.
- Run merge once per user (lazy on first list after deploy or SQL job).
