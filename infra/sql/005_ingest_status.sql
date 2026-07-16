-- Ingest progress dashboard snapshot (ops Workbook / future app).
-- Apply:
--   docker compose exec -T db psql -U postgres -d neighborhoodiq < infra/sql/005_ingest_status.sql

CREATE TABLE IF NOT EXISTS ingest_status_snapshot (
    scope VARCHAR(32) NOT NULL,
    job_name VARCHAR(32) NOT NULL,
    pct_complete NUMERIC(5,1) NOT NULL DEFAULT 0,
    done_count INTEGER NOT NULL DEFAULT 0,
    total_count INTEGER NOT NULL DEFAULT 0,
    detail JSONB,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (scope, job_name)
);

CREATE INDEX IF NOT EXISTS idx_ingest_status_captured
    ON ingest_status_snapshot (captured_at DESC);
