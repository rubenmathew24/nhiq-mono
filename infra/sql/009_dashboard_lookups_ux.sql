-- 009: Dashboard lookups UX — favorites, activity, dedupe flag
-- Idempotent for Azure / local apply.

ALTER TABLE saved_lookups
  ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE saved_lookups
  ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ;

UPDATE saved_lookups
SET last_activity_at = COALESCE(last_activity_at, created_at, NOW())
WHERE last_activity_at IS NULL;

ALTER TABLE saved_lookups
  ALTER COLUMN last_activity_at SET DEFAULT NOW();

ALTER TABLE saved_lookups
  ALTER COLUMN last_activity_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_saved_lookups_user_activity
  ON saved_lookups (user_id, last_activity_at DESC);

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS lookups_deduped_at TIMESTAMPTZ;
