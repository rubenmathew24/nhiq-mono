# TEMPORARY: File-backed lookup store for UI development only.
# DELETE when Postgres address_lookups table is implemented.
# See specs/001-web-app-pages/research.md removal checklist.

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.schemas.auth import SavedLookup


# apps/api/app/services/lookup_store.py → parents[2] == apps/api
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
LOOKUPS_FILE = DATA_DIR / "TEMP_dev_lookups.jsonl"


@runtime_checkable
class LookupStore(Protocol):
    def list_for_user(self, user_id: str) -> list[SavedLookup]: ...


class FileLookupStore:
    """TEMPORARY file-backed implementation. Replace with Postgres repository."""

    def _read_all(self) -> list[SavedLookup]:
        if not LOOKUPS_FILE.exists():
            return []
        lookups: list[SavedLookup] = []
        with LOOKUPS_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    lookups.append(SavedLookup(**json.loads(line)))
        return lookups

    def list_for_user(self, user_id: str) -> list[SavedLookup]:
        all_lookups = self._read_all()
        user_lookups = [lk for lk in all_lookups if lk.user_id == user_id]
        return sorted(user_lookups, key=lambda lk: lk.looked_up_at, reverse=True)


lookup_store: LookupStore = FileLookupStore()
