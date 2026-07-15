-- One-shot for existing Compose volumes that already ran init.sql.
-- Safe to re-run.

ALTER TABLE neighborhood_scores
  ADD COLUMN IF NOT EXISTS score_sources JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN neighborhood_scores.score_sources IS
  'Per-dimension provenance: {dimension: {source_id, reason, ...}}. EPA primary; Open-Meteo fallback for environment.';
