"""Shared loader for scripts/apply-sql-migrations.py (hyphenated filename)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "scripts" / "apply-sql-migrations.py"


def load_migrate_module():
    spec = importlib.util.spec_from_file_location("apply_sql_migrations", _SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
