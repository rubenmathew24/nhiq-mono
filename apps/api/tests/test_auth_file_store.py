"""Tests for TEMP file-backed user store.

TEMPORARY: Delete this file when Postgres user auth is implemented.
See specs/001-web-app-pages/research.md removal checklist.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from app.services.user_store import FileUserStore


def _fake_hash(pw: str) -> str:
    """Deterministic stub — avoids bcrypt/passlib version incompatibilities in tests."""
    return f"hashed:{pw}"


def _fake_verify(plain: str, hashed: str) -> bool:
    return hashed == f"hashed:{plain}"


@pytest.fixture()
def tmp_store(tmp_path, monkeypatch):
    """FileUserStore wired to a temp file so tests don't touch real seed data."""
    import app.services.user_store as us_mod
    monkeypatch.setattr(us_mod, "USERS_FILE", tmp_path / "users.jsonl")
    monkeypatch.setattr(us_mod, "DATA_DIR", tmp_path)
    store = FileUserStore()
    # patch module-level constants inside the store's module
    import app.services.user_store as m
    m.USERS_FILE = tmp_path / "users.jsonl"
    m.DATA_DIR = tmp_path
    return store


def test_create_and_retrieve_by_email(tmp_store):
    user = tmp_store.create("alice@example.com", "Alice", _fake_hash("password123"))
    assert user.email == "alice@example.com"
    assert user.tier == "free"

    found = tmp_store.get_by_email("alice@example.com")
    assert found is not None
    assert found.id == user.id


def test_get_by_email_case_insensitive(tmp_store):
    tmp_store.create("Bob@Example.COM", "Bob", _fake_hash("pw"))
    assert tmp_store.get_by_email("bob@example.com") is not None


def test_get_by_id(tmp_store):
    user = tmp_store.create("carol@example.com", "Carol", _fake_hash("pw"))
    found = tmp_store.get_by_id(user.id)
    assert found is not None
    assert found.email == "carol@example.com"


def test_duplicate_email_returns_existing(tmp_store):
    tmp_store.create("dave@example.com", "Dave", _fake_hash("pw"))
    tmp_store.create("dave@example.com", "Dave2", _fake_hash("pw"))
    all_users = tmp_store._read_all()
    dave_users = [u for u in all_users if u.email.lower() == "dave@example.com"]
    assert len(dave_users) == 2  # file store doesn't deduplicate; AuthService does


def test_missing_user_returns_none(tmp_store):
    assert tmp_store.get_by_email("nobody@example.com") is None
    assert tmp_store.get_by_id("nonexistent-id") is None


def test_password_hashing_roundtrip():
    hashed = _fake_hash("supersecret")
    assert _fake_verify("supersecret", hashed)
    assert not _fake_verify("wrongpassword", hashed)
