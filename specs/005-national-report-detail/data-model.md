# Data Model: National Report Detail Ingest

**Feature**: `005-national-report-detail` | **Date**: 2026-07-16

Additive production use of schema already defined in `infra/sql/007_report_detail.sql` and ACS population column. No new tables beyond 004.

---

## Entities (reuse)

| Entity | Storage | Role |
|--------|---------|------|
| NeighborhoodScore | `neighborhood_scores` | Category scores + `score_detail` JSONB (expand UI) |
| FemaNriTract | `fema_nri_tracts` | Tract hazard / composite risk |
| HospitalTimelyMeasure | `hospital_timely_measures` | Facility timely-care / ER wait |
| AcsIndicator | `acs_indicators` | Labor/income + **`total_population`** (B01003) |
| GeoCounty | `geo_counties` | National universe for inventory |
| IngestStatusSnapshot | `ingest_status_snapshot` | Ops % including new jobs |

### Identity / uniqueness (unchanged)

- `neighborhood_scores`: `(geoid, data_vintage)`
- `fema_nri_tracts`: `geoid` PK
- `hospital_timely_measures`: `(cms_provider_id, measure_id, data_vintage)`
- `acs_indicators`: `(geoid, geo_level, acs_year)`

---

## Completeness rules (inventory)

| Worker | Unit done when |
|--------|----------------|
| Base (census…bls) | Existing 003 checkpoints |
| **acs** | Tract rows exist for county **and** `total_population IS NOT NULL` on those tracts; state geo_level pop present for state FIPS when state is in scope |
| **fema** | Every census tract geoid in county has a `fema_nri_tracts` row |
| **cms_timely** | Every `hospitals.cms_provider_id` in the state has ≥1 timely measure for active vintage (or documented “no measures in source” skip set — prefer: missing providers ⇒ state still gapped until worker ran and found none; after run, empty result still marks providers attempted — implement as: state done when worker completed upsert pass for all providers **or** each provider has ≥1 row; simplest v1: state done iff all in-scope providers appear in `hospital_timely_measures` for vintage **or** hospital count is 0) |
| **scoring** | Every tract in county has `score_sources.safety.source_id = fbi_cde` **and** `score_detail` is not null/empty `{}` for active vintage |

---

## State classes (orchestrator)

| Class | Meaning |
|-------|---------|
| **Report-detail backfill (A)** | Base workers complete for all counties in state; at least one of acs-pop / fema / cms_timely / scoring-detail still gapped |
| **Virgin / other (B)** | Any base-pipeline gap remains |
| **Done** | No pipeline gaps |

Selection (normal max_states): process A before B.

---

## Relationships

```text
geo_counties → counties in national universe
census_tracts 1──0..1 fema_nri_tracts
hospitals 1──* hospital_timely_measures
acs_indicators (tract/state) → scoring safety rates + economy stats
neighborhood_scores.score_detail ← scoring after fema/timely/acs inputs
```

---

## Validation

- Applying `007` on populated DB must not drop rows.
- Empty `score_detail` remains valid API input (limited expand) until scoring gap closed.
- Re-score may change category numerics when hazard/timeliness enter the blend — accepted.
