"""Test configuration — set required environment variables before app imports."""

import os

# Provide minimal settings so pydantic-settings doesn't fail on required fields.
# These are test-only values; no real database or Redis is needed.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
