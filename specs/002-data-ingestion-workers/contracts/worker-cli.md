# Contract: Local Worker CLI (Docker Compose)

**Feature**: `002-data-ingestion-workers` | **Date**: 2026-07-14 (reopened)

One-off batch jobs against Compose `db`. No HTTP API between workers and the app.

## Common environment

| Variable | Required | Notes |
|----------|----------|--------|
| `DATABASE_URL` | yes | In Compose: `postgresql://postgres:postgres@db:5432/neighborhoodiq` |
| `LOG_LEVEL` | no | default `INFO` |
| `EPA_AQS_EMAIL` / `EPA_AQS_KEY` | EPA only | Fail fast if missing when running EPA |
| `EPA_END_LAG_DAYS` / `EPA_LOOKBACK_DAYS` | no | Defaults in `fixtures/constants.py` |
| `MAPBOX_TOKEN` | API UI verify | Workers do not require Mapbox for CMS ZIP geocode |
| `REDIS_URL` | scoring (optional) | Best-effort report cache invalidation |
| `FBI_CDE_API_KEY` | **R1 fbi** | Required for safety phase; fail fast if missing |
| `FBI_CDE_*` | no | Optional chart knobs — see research.md §8 |
| `CENSUS_API_KEY` | R3 acs (recommended) | ACS API quota |
| BLS API registration | R3 bls | Per BLS Public Data API v2 |

## Commands (Compose profiles)

Assume repo root and `.env` present.

### MVP baseline (done)

```bash
docker compose up -d db redis

docker compose --profile workers run --rm worker-census
docker compose --profile workers run --rm worker-epa
docker compose --profile workers run --rm worker-cms
docker compose --profile workers run --rm worker-scoring
```

### Reopen phases

```bash
# R1 — safety (FBI CDE)
docker compose --profile workers run --rm worker-fbi
docker compose --profile workers run --rm worker-scoring

# R2 — education (NCES + Urban)
docker compose --profile workers run --rm worker-nces
docker compose --profile workers run --rm worker-urban
docker compose --profile workers run --rm worker-scoring

# R3 — economic (ACS + BLS LAUS)
docker compose --profile workers run --rm worker-acs
docker compose --profile workers run --rm worker-bls
docker compose --profile workers run --rm worker-scoring
```

| Service | Module entry | Success criteria |
|---------|--------------|------------------|
| `worker-census` | `python -m ingest.census.run` | Tracts for fixture counties |
| `worker-epa` | `python -m ingest.epa.run` | AQI upsert; empty counties OK |
| `worker-cms` | `python -m ingest.cms.run` | Hospitals + ZIP geometry |
| `worker-scoring` | `python -m scoring.compute` | All fixture-county tracts; vintage `2026-Q3`; placeholders only for undelivered dimensions |
| `worker-fbi` | `python -m ingest.fbi.run` | **R1**: CDE load for fixture counties; no faux-empty success without key |
| `worker-nces` | `python -m ingest.nces.run` | **R2**: NCES schools w/ geometry for fixture geographies |
| `worker-urban` | `python -m ingest.urban.run` | **R2**: Urban directory rows joinable on `ncessch` |
| `worker-acs` | `python -m ingest.acs.run` | **R3**: ACS indicators for fixture tracts/counties |
| `worker-bls` | `python -m ingest.bls.run` | **R3**: LAUS unemployment series for fixture counties |

## Operational notes

- **CMS**: No native lat/lng — ZIP geocode.
- **EPA**: Empty Benton County OK; Open-Meteo at score time.
- **FBI (R1)**: Agency-grain CDE charts; `FBI_CDE_API_KEY` required.
- **Education (R2)**: NCES authoritative locations; Urban complementary stats; join `ncessch`.
- **Economic (R3)**: ACS + LAUS complementary; Zillow/Redfin out of scope.

## Exit / logging contract

- Consistent logs: source name, unit, counts, errors.
- Missing required secrets → non-zero exit + message naming the variable.
- Partial unit failure → log error; continue others; final summary includes failures.
- Idempotent: second identical run does not increase unique natural-key counts.
- Dual-source phases: never claim both succeeded if one failed.

## Out of scope

- Azure Container Apps Job definitions
- Cron / scheduled triggers
- Publishing images to ACR
- FEMA NRI / Zillow / Redfin / HUD FMR workers
- Source-showcase UI
