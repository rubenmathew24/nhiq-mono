# Quickstart: National Coverage Dashboard

1. Ensure Postgres has `geo_counties` bootstrapped and some ingest/scoring data.
2. Run API (`apps/api`) with `DATABASE_URL` pointing at that DB.
3. Run web with `NEXT_PUBLIC_API_URL` set.
4. Open `http://localhost:3000/coverage` (no login).
5. Confirm **Overall** and **By state** tabs; on By state, filter includes **Overall** plus each source. Scoring total ≈ national county count.

API smoke: `GET http://localhost:8000/api/v1/coverage` (see `/api/docs`).
