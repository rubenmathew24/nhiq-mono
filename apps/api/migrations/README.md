# API schema & migrations

## Local / Docker Compose (current)

**Source of truth for local databases** is `infra/sql/init.sql`, mounted into the Compose
`db` service on first volume create. Optional deltas/seeds: `infra/sql/seed_demo_auth.sql`.

```powershell
# Fresh schema only applies on empty pgdata volumes
docker compose up -d db

# Apply helper ALTERs / demo address row (safe to re-run)
Get-Content infra/sql/seed_demo_auth.sql | docker compose exec -T db psql -U postgres -d neighborhoodiq
```

## Alembic (future / non-Compose environments)

`alembic` remains in `requirements.txt` for Azure and multi-instance deploys. This folder is
reserved for Alembic revision scripts when we stop relying solely on `init.sql`.

Until then:

- Do **not** run `alembic upgrade` against Compose `db` unless you add matching revisions
  that are idempotent with `init.sql`.
- Prefer extending `infra/sql/init.sql` + `seed_demo_auth.sql` for local schema changes.
