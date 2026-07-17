-- Report sub-scores: score_detail JSONB + FEMA NRI + CMS Timely measures.
-- Apply on existing Compose volumes after init.sql bootstrap:
--   psql "$DATABASE_URL" -f infra/sql/007_report_detail.sql

ALTER TABLE neighborhood_scores
  ADD COLUMN IF NOT EXISTS score_detail JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN neighborhood_scores.score_detail IS
  'Per-dimension sub_scores + expand stats for report UI.';

CREATE TABLE IF NOT EXISTS fema_nri_tracts (
    geoid VARCHAR(11) PRIMARY KEY,
    state_fips VARCHAR(2),
    county_fips VARCHAR(3),
    risk_score NUMERIC(12,4),
    risk_rating VARCHAR(64),
    eal_score NUMERIC(12,4),
    sovi_score NUMERIC(12,4),
    resl_score NUMERIC(12,4),
    hazards JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_vintage VARCHAR(10) NOT NULL DEFAULT '2026-Q3',
    payload JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fema_nri_county ON fema_nri_tracts (state_fips, county_fips);

CREATE TABLE IF NOT EXISTS hospital_timely_measures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cms_provider_id VARCHAR(10) NOT NULL,
    measure_id VARCHAR(32) NOT NULL,
    measure_name VARCHAR(255),
    score_value NUMERIC(12,4),
    score_text VARCHAR(64),
    sample NUMERIC(12,2),
    footnote TEXT,
    state_score NUMERIC(12,4),
    national_score NUMERIC(12,4),
    start_date DATE,
    end_date DATE,
    data_vintage VARCHAR(10) NOT NULL DEFAULT '2026-Q3',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (cms_provider_id, measure_id, data_vintage)
);
CREATE INDEX IF NOT EXISTS idx_timely_provider ON hospital_timely_measures (cms_provider_id);
