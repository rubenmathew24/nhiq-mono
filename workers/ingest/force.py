"""INGEST_FORCE — bypass skip-done checkpoints for a full re-upsert run."""

from __future__ import annotations

import os


def force_enabled(env: dict[str, str] | None = None) -> bool:
    """True when INGEST_FORCE is 1/true/yes (case-insensitive)."""
    source = env if env is not None else os.environ
    raw = (source.get("INGEST_FORCE") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")
