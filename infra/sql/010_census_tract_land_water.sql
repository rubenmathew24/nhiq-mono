-- 010: Census tract TIGER land/water area (ALAND / AWATER, square meters).
-- Idempotent for Azure / local apply.
-- Fresh volumes: also covered by infra/sql/init.sql.
--
-- Why: Water-only tracts (ALAND = 0), e.g. Lake Michigan, must stay in the
-- warehouse for county coverage but Discover excludes them from choropleth
-- fills and city snapshot stats. Existing rows stay NULL until census re-ingest
-- (force or pending counties); NULL is treated as land until backfill.

ALTER TABLE census_tracts
  ADD COLUMN IF NOT EXISTS aland BIGINT;

ALTER TABLE census_tracts
  ADD COLUMN IF NOT EXISTS awater BIGINT;

COMMENT ON COLUMN census_tracts.aland IS
  'TIGER ALAND land area in square meters; 0 = water-only tract.';

COMMENT ON COLUMN census_tracts.awater IS
  'TIGER AWATER water area in square meters.';

CREATE INDEX IF NOT EXISTS idx_census_tracts_aland_zero
  ON census_tracts (aland)
  WHERE aland = 0;
