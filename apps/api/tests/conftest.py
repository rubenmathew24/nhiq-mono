"""Test configuration — set required environment variables before app imports."""

import os

# Host-run pytest → Compose Postgres published on 5433 (see docker-compose.yml).
# Service hostname `db:5432` only works on the Docker network.
os.environ["DATABASE_URL"] = (
    "postgresql://postgres:postgres@localhost:5433/neighborhoodiq"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("ENVIRONMENT", "test")
