# Contract: Worker CLI (report detail ingest)

**Feature**: `004-report-subscores` | **Date**: 2026-07-16

Local Docker Compose one-off workers. Scope: **`INGEST_SCOPE=smoke`** or **`metro_10`** only for this feature’s new jobs.

## New / updated services

| Compose service | Module | Writes | Notes |
|-----------------|--------|--------|-------|
| `worker-fema` | `python -m ingest.fema.run` | `fema_nri_tracts` | ArcGIS NRI tracts for `active_county_fips()` |
| `worker-cms-timely` | `python -m ingest.cms_timely.run` | `hospital_timely_measures` | Timely & Effective Care for hospitals in scope states |
| `worker-scoring` | `python -m scoring.compute` | `neighborhood_scores` including **`score_detail`** | Existing entrypoint; extended behavior |

## Required env

| Variable | Used by | Notes |
|----------|---------|--------|
| `DATABASE_URL` | all | Compose `@db:5432` |
| `INGEST_SCOPE` | fema, cms_timely, scoring | `smoke` \| `metro_10` — **do not** run these new workers with `national` in this feature |
| `SCORE_DATA_VINTAGE` / vintage constant | scoring | Align with API |
| Existing EPA/FBI/etc. | prior workers | Unchanged |

No new API keys required for public FEMA FeatureServer or CMS Provider Data Catalog (rate-limit politely).

## Suggested operator order (dev)

```text
# Schema
psql < infra/sql/007_report_detail.sql   # or documented filename

# Optional if raw base data missing for scope:
worker-census → worker-epa → worker-cms → worker-fbi → worker-nces → worker-urban → worker-acs → worker-bls

# This feature
INGEST_SCOPE=smoke|metro_10  worker-fema
INGEST_SCOPE=smoke|metro_10  worker-cms-timely
INGEST_SCOPE=smoke|metro_10  worker-scoring
```

## Exit behavior

- Missing DB / schema → non-zero + clear message.
- `INGEST_SCOPE=national` on fema/cms_timely in this feature → refuse with message pointing to future national work (or skip with loud log — prefer **refuse**).
- Partial county success → checkpoint skips on re-run; scoring still produces air/access detail without hazard/timely when tables empty.

## Idempotency

Upsert natural keys per [data-model.md](../data-model.md). Re-score overwrites `score_detail` for `(geoid, data_vintage)`.
