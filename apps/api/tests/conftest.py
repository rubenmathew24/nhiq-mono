"""Test configuration — set required environment variables before app imports."""

import os

# Prefer Compose/service env when present (api container uses `@db:5432`).
# Host-run pytest falls back to published Postgres on localhost:5433.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/neighborhoodiq",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("ENVIRONMENT", "test")
