# Quickstart: 009-dashboard-lookups-ux

## Prerequisites

- Docker Compose API + web + Postgres (+ Redis) with a signed-in user
- `NEXT_PUBLIC_MAPBOX_TOKEN` (public token) set for web
- `MAPBOX_TOKEN` set for API geocoding
- Scored data present for at least one tract (`SCORE_DATA_VINTAGE` aligned)

## Validate address lookahead

1. Open `/dashboard` signed in.
2. Type 3+ characters of a U.S. street address.
3. Expect a suggestion dropdown; select one → field fills → Score it → report opens.
4. With Mapbox token cleared/blocked: typing still allows free-text submit; no hard crash.

## Validate dedupe + score preview

1. Score the same address twice while signed in.
2. Dashboard shows **one** saved identity (may appear in Favorites and Recent if favorited).
3. Row shows overall score with the same color band as the report, or an unavailable state if unscored.

## Validate Favorites / Recent / menu

1. Open ⋯ → Favorite → address appears under Favorites and still under Recent.
2. Open the report (or re-search) → entry rises to top of Recent (and Favorites if favorited).
3. ⋯ → Delete → confirm cancel → still present; confirm OK → gone from both columns.

## Validate merge of legacy duplicates

1. Seed two `saved_lookups` for the same user pointing at two `address_lookups` with the same `geoid`.
2. Hit `GET /api/v1/users/me/lookups`.
3. Expect a single item for that place afterward.

## Automated checks

```bash
# API
cd apps/api && pytest tests/test_user_lookups.py -q

# Web (after tests added)
cd apps/web && npm test -- --run src/__tests__/
```

See [contracts/dashboard-lookups-api.md](./contracts/dashboard-lookups-api.md) and [data-model.md](./data-model.md).
