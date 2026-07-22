# Data Model: 010-cicd-prod-deploy

This feature is primarily CI/CD. The only durable production schema addition is migration bookkeeping.

## Entity: `schema_migrations`

| Field | Type | Notes |
|-------|------|--------|
| `filename` | `TEXT` PK | Exact migration basename, e.g. `009_dashboard_lookups_ux.sql` |
| `applied_at` | `TIMESTAMPTZ` NOT NULL | Default `now()` |

**Rules**:
- Inserted only after a successful apply of that file.
- Never delete rows as part of routine Deploy (no “down” migrations in v1).
- `init.sql` and `seed_*.sql` are **not** tracked as numbered migrations.

**Relationships**: None to product tables; orthogonal bookkeeping.

## Logical: Deploy change set (ephemeral)

Not stored in Postgres. Computed per workflow run:

| Field | Type | Meaning |
|-------|------|---------|
| `web` | bool | Rebuild/redeploy web |
| `api` | bool | Rebuild/redeploy API |
| `schema` | bool | Run migration runner |
| `app_config` | bool | Sync Container App env from manifest |
| `force_full` | bool | Dispatch-only override |

## Logical: App env manifest (repo file)

File: `infra/deploy/app-env.manifest.json`

```json
{
  "api": ["DATABASE_URL", "REDIS_URL", "SECRET_KEY", "..."],
  "web": ["NEXT_PUBLIC_API_URL", "..."]
}
```

Values are **not** in the file; only required names. Deploy maps names → existing secret sources.

## Out of scope entities

- No changes to `saved_lookups`, scores, Redis key schema, or worker job definitions for this feature’s core path (except asserting existing columns in CI).
