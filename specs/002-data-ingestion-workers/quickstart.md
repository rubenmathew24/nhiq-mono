# Quickstart: Data Ingestion Workers (local Docker)

**Feature**: `002-data-ingestion-workers` | **Date**: 2026-07-14 (reopened)

Validate fixture-county ingest → score → live report. See [contracts/worker-cli.md](./contracts/worker-cli.md), [contracts/score-api.md](./contracts/score-api.md), [data-model.md](./data-model.md), [research.md](./research.md).

**Out of scope here**: Azure, `master` deploy, national ingest, FEMA NRI, Zillow/Redfin, source-showcase UI. Open-Meteo remains a **scoring-time AQ fallback** only.

**Delivery phases**: MVP (healthcare + environment) is done. Reopen: **R1 safety (FBI CDE)** → **R2 education (NCES + Urban)** → **R3 economic (ACS + BLS LAUS)**.

## Prerequisites

- Docker Desktop running
- Repo `.env` from `.env.example` with at least:
  - `DATABASE_URL` (Compose default to `db:5432` is fine inside containers)
  - `MAPBOX_TOKEN` + `NEXT_PUBLIC_MAPBOX_TOKEN` (lookup + map)
  - `EPA_AQS_EMAIL` + `EPA_AQS_KEY` ([EPA AQS signup](https://aqs.epa.gov/data/api/signup))
  - `SCORE_DATA_VINTAGE=2026-Q3` (must match `workers/ingest/fixtures/constants.py`)
  - **R1**: `FBI_CDE_API_KEY` ([api.data.gov](https://api.data.gov/signup/))
  - **R3**: `CENSUS_API_KEY` recommended; BLS Public Data API access as required by BLS
  - Auth secrets if you use signed-in flows (`AUTH_SECRET` / `SECRET_KEY`)
- Feature branch `002-data-ingestion-workers` checked out

### Open-Meteo note (environment fallback)

When EPA monitors are missing/sparse for a fixture county, `worker-scoring` calls the public Open-Meteo Air Quality API (`us_aqi`, CAMS-modeled). Treat values as **modeled**, not regulatory monitor AQI. [Commercial use may require an Open-Meteo license](https://open-meteo.com/en/pricing). Provenance is stored in `neighborhood_scores.score_sources.environment`.

## Setup

1. Start core stack:

   ```bash
   docker compose up -d db redis api web
   ```

2. Confirm API: `http://localhost:8000/health` → 200; web: `http://localhost:3000`.

3. Ensure schemas exist. Fresh volume picks up `infra/sql/init.sql`. Existing volumes:

   ```bash
   docker compose exec -T db psql -U postgres -d neighborhoodiq < infra/sql/002_raw_ingest_tables.sql
   docker compose exec -T db psql -U postgres -d neighborhoodiq < infra/sql/003_score_sources.sql
   # After R1–R3 migrations land:
   docker compose exec -T db psql -U postgres -d neighborhoodiq < infra/sql/004_safety_education_economic.sql
   ```

4. MVP workers (already proven):

   ```bash
   docker compose --profile workers run --rm worker-census
   docker compose --profile workers run --rm worker-epa
   docker compose --profile workers run --rm worker-cms
   docker compose --profile workers run --rm worker-scoring
   ```

### V10 — Census land/water (ALAND / AWATER)

For existing Compose volumes (not a fresh `init.sql`):

```bash
# From repo root — or use scripts/apply-sql-migrations.py against DATABASE_URL
docker compose exec -T db psql -U postgres -d neighborhoodiq < infra/sql/010_census_tract_land_water.sql
```

Then re-ingest tracts so `aland`/`awater` fill (checkpoint skip otherwise leaves NULL):

```bash
INGEST_FORCE=1 docker compose --profile workers run --rm -e INGEST_FORCE=1 worker-census
```

Confirm water-only Cook County tracts:

```bash
docker compose exec db psql -U postgres -d neighborhoodiq -c \
  "SELECT geoid, aland, awater FROM census_tracts
   WHERE county_fips='031' AND state_fips='17' AND aland = 0 LIMIT 5;"
```

Discover (008) excludes `aland = 0` from fills/summary; NULL `aland` still displays as land until this backfill.

## Validation scenarios

### V1–V6 — MVP (healthcare + environment)

Same as prior close-out: EPA coverage some counties; census tracts; CMS hospitals+geometry; score count ≈ tract count; Bentonville live report matches DB; FBI was skeleton (superseded by V7).

### V7 — Safety (R1)

1. Set `FBI_CDE_API_KEY` in `.env`.
2. Run `worker-fbi` then `worker-scoring`.
3. Expect CDE agency/offense rows for fixture counties; Bentonville tracts leave safety placeholder:

   ```bash
   docker compose exec db psql -U postgres -d neighborhoodiq -c \
     "SELECT geoid, safety_score, score_sources->'safety' AS safety_src
      FROM neighborhood_scores WHERE geoid LIKE '05007%' AND data_vintage='2026-Q3' LIMIT 3;"
   ```

4. Bentonville report: `sources.safety.source_id` is `fbi_cde` (or documented `default`), not `placeholder`.
5. Education/economic may still be placeholders.

### V8 — Education (R2)

1. Run `worker-nces` → `worker-urban` → `worker-scoring`.
2. Confirm NCES geometry + Urban join keys for fixture geographies.
3. Bentonville: `education_score` non-placeholder; `score_sources.education` references both contributors.

### V9 — Economic (R3)

1. Run `worker-acs` → `worker-bls` → `worker-scoring`.
2. Confirm ACS tract/county rows + LAUS county rates for fixture set.
3. Bentonville: `economic_score` non-placeholder; `score_sources.economic` references ACS + LAUS.
4. Overall score reflects all five source-backed dimensions for fixture counties.

## Sanity SQL helpers

```bash
docker compose exec db psql -U postgres -d neighborhoodiq -c \
  "SELECT geoid, overall_score, healthcare_score, safety_score, education_score,
          environment_score, economic_score, score_sources
   FROM neighborhood_scores WHERE data_vintage = '2026-Q3'
   ORDER BY computed_at DESC LIMIT 5;"
```

## Done when

- [x] V1–V6 MVP pass locally
- [x] V7 safety phase passes (FBI CDE + non-placeholder safety) — Bentonville (`05007%`) tracts show `score_sources.safety.source_id=fbi_cde`; worker fail-fast verified without key. **Note:** upstream CDE 503s may leave non-Benton fixture counties on `default` until a clean `worker-fbi` re-run
- [x] V8 education phase passes (NCES + Urban) — fixture schools loaded; Bentonville `education` source `nces_urban`
- [x] V9 economic phase fully dual-source — ACS tract indicators + BLS LAUS loaded; Bentonville `economic` source `acs_bls_laus` (`CENSUS_API_KEY` required for ACS)
- [ ] V10 TIGER land/water — apply `010_census_tract_land_water.sql`, force `worker-census`, confirm Cook County `aland = 0` rows (see V10 section above)
- [x] No Azure / master steps required
- [x] Operators understand EPA sparsity + CMS ZIP + dual-source complementarity notes
