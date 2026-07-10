"""Tests for GET /users/me/lookups via TEMP file lookup store.

TEMPORARY: Replace with DB fixture tests when Postgres ships.
"""

import json
import pytest
from pathlib import Path
from app.services.lookup_store import FileLookupStore
from app.schemas.auth import SavedLookup


@pytest.fixture()
def tmp_lookup_store(tmp_path, monkeypatch):
    import app.services.lookup_store as lm
    monkeypatch.setattr(lm, "LOOKUPS_FILE", tmp_path / "lookups.jsonl")
    monkeypatch.setattr(lm, "DATA_DIR", tmp_path)
    store = FileLookupStore()
    lm.LOOKUPS_FILE = tmp_path / "lookups.jsonl"
    lm.DATA_DIR = tmp_path
    return store, tmp_path / "lookups.jsonl"


def test_empty_lookups(tmp_lookup_store):
    store, _ = tmp_lookup_store
    assert store.list_for_user("user-1") == []


def test_seeded_lookups(tmp_lookup_store):
    store, lookups_file = tmp_lookup_store
    entry = {
        "user_id": "user-1",
        "address_id": "addr-001",
        "address_normalized": "123 Main St",
        "looked_up_at": "2026-07-10T10:00:00Z",
    }
    lookups_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    results = store.list_for_user("user-1")
    assert len(results) == 1
    assert results[0].address_id == "addr-001"


def test_lookups_filtered_by_user(tmp_lookup_store):
    store, lookups_file = tmp_lookup_store
    rows = [
        {"user_id": "user-1", "address_id": "a1", "address_normalized": "A1", "looked_up_at": "2026-07-09T10:00:00Z"},
        {"user_id": "user-2", "address_id": "b1", "address_normalized": "B1", "looked_up_at": "2026-07-09T11:00:00Z"},
    ]
    lookups_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert len(store.list_for_user("user-1")) == 1
    assert len(store.list_for_user("user-2")) == 1
    assert store.list_for_user("user-1")[0].address_id == "a1"


def test_lookups_sorted_newest_first(tmp_lookup_store):
    store, lookups_file = tmp_lookup_store
    rows = [
        {"user_id": "u1", "address_id": "old", "address_normalized": "Old", "looked_up_at": "2026-07-08T10:00:00Z"},
        {"user_id": "u1", "address_id": "new", "address_normalized": "New", "looked_up_at": "2026-07-10T10:00:00Z"},
    ]
    lookups_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    results = store.list_for_user("u1")
    assert results[0].address_id == "new"
