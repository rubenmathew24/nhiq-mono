# Research: 009-dashboard-lookups-ux

## 1. Why duplicates exist today

**Decision**: Treat “same address” as the same resolved place via **census tract `geoid`** when present, else normalized address string equality; stop inserting a new `address_lookups` row on every search when a matching place already exists for reuse by that user.

**Rationale**: `saved_lookups` already has `UNIQUE(user_id, address_lookup_id)`, but `record_lookup` always inserts a **new** `address_lookups` row, so the unique constraint never collapses “same house, new search.” Users therefore see multiple dashboard rows for one place.

**Alternatives considered**:
- Unique on `(user_id, address_normalized)` only — fragile with Mapbox formatting drift
- Unique on lat/lng rounded — noisy near boundaries
- UI-only hide duplicates — leaves dirty data (rejected by clarify: merge)

## 2. Address lookahead

**Decision**: Use **Mapbox Places Autocomplete** from the browser with `NEXT_PUBLIC_MAPBOX_TOKEN` (`pk.*`), US + address types, debounce ~200–300ms, min 3 characters; selecting a suggestion fills the input and submits the existing `/api/v1/lookup` flow.

**Rationale**: Constitution II explicitly allows Mapbox Places from the client; keeps secrets for Geocoding (`sk.*`) server-side. Shared `AddressSearch` may also improve landing search without extra scope work.

**Alternatives considered**:
- Server proxy for every keystroke — extra latency/load; unnecessary given constitution carve-out
- Census-only suggestions — poor street-level UX

## 3. Score preview on list

**Decision**: Enrich `GET /api/v1/users/me/lookups` with `overall_score: number | null` by joining each entry’s `geoid` to `neighborhood_scores` for `SCORE_DATA_VINTAGE`. Web reuses `scoreTextClass` / `scoreGrade` from `apps/web/src/lib/utils.ts` (same bands as report).

**Rationale**: Precomputed path (Constitution III); one round-trip for dashboard. Null → unavailable UI, not a fake score.

**Alternatives considered**:
- N+1 client calls to `/score/{id}` — slow, chatty
- Caching overall scores on `saved_lookups` — stale vs vintage updates

## 4. Favorites + Recent (dual listing)

**Decision**: Add `is_favorite: bool` (default false) and `last_activity_at: timestamptz` on `saved_lookups`. API returns a flat enriched list; web derives Favorites (`is_favorite`) and Recent (all entries sorted by `last_activity_at` desc). Favoriting does not remove from Recent.

**Rationale**: Matches clarify dual-listing; single identity; simple client split.

**Alternatives considered**:
- Mutually exclusive columns — rejected in clarify
- Separate favorites table — unnecessary indirection

## 5. Activity / recency bumps

**Decision**: Update `last_activity_at` when (1) user completes a lookup that attaches/updates their saved entry, and (2) user opens a report for an address they own — via authenticated `POST /api/v1/users/me/lookups/{address_id}/touch` called from the report page (or dashboard link click).

**Rationale**: Spec requires both re-search and open-report to bump recency; touch endpoint keeps report SSR simple and explicit.

**Alternatives considered**:
- Infer touch inside `GET /score/{id}` when Bearer present — couples scoring to dashboard semantics
- Client-only sort — not durable across devices

## 6. Duplicate merge (one-time)

**Decision**: Service method `merge_duplicate_saved_lookups(user_id)` (idempotent): group user’s saved rows by place key (`geoid` or normalized address); keep one survivor (max `last_activity_at` / `created_at`); OR `is_favorite` across group; delete other `saved_lookups` rows. Call from list endpoint once per user (flag/`merged_at`) or as a migration script run at deploy + defensive call on list.

**Rationale**: Clarify required cleanup; keeping merge in service enables tests and safe re-runs.

**Alternatives considered**:
- Leave old duplicates — rejected
- UI hide only — rejected

## 7. Delete confirmation

**Decision**: Client-side confirm dialog before `DELETE /api/v1/users/me/lookups/{address_id}`; server deletes only the user’s `saved_lookups` row (not shared `address_lookups` / scores).

**Rationale**: Clarify A; accidental menu clicks are common.

## 8. Post-design constitution re-check

All gates remain satisfied: Places-only client external call; enrichment from `neighborhood_scores`; auth on mutate routes; tests planned.
