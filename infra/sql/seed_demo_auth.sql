-- Optional local helpers after init.sql (Docker Compose `db`).
-- Does NOT insert a login password — register via /register, then re-run to attach a demo saved lookup.
--
-- Usage (repo root, db up):
--   Get-Content infra/sql/seed_demo_auth.sql | docker compose exec -T db psql -U postgres -d neighborhoodiq

-- Ensure auth-related columns exist on volumes created before Phase 13
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE saved_lookups ADD COLUMN IF NOT EXISTS notes TEXT;

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);
CREATE INDEX IF NOT EXISTS idx_saved_lookups_user ON saved_lookups(user_id);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'saved_lookups_user_id_address_lookup_id_key'
  ) THEN
    ALTER TABLE saved_lookups
      ADD CONSTRAINT saved_lookups_user_id_address_lookup_id_key
      UNIQUE (user_id, address_lookup_id);
  END IF;
END $$;

-- Demo address row with coordinates so /report/{id} can build a mock score from Postgres
INSERT INTO address_lookups (id, address_raw, address_normalized, latitude, longitude, geoid)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    '1600 Pennsylvania Avenue NW, Washington, DC',
    '1600 Pennsylvania Avenue NW, Washington, DC',
    38.8977,
    -77.0365,
    '11001006202'
)
ON CONFLICT (id) DO UPDATE SET
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    geoid = EXCLUDED.geoid,
    address_normalized = EXCLUDED.address_normalized;

-- Attach demo address to the most recently created user (if any)
INSERT INTO saved_lookups (user_id, address_lookup_id, label)
SELECT u.id, '22222222-2222-2222-2222-222222222222'::uuid, 'Demo saved lookup'
FROM users u
ORDER BY u.created_at DESC
LIMIT 1
ON CONFLICT (user_id, address_lookup_id) DO NOTHING;
