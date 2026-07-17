"""Tests for dev-scope guard (refuse national)."""

import os
import pytest

from ingest.geo.scope import assert_dev_scope


def test_assert_dev_scope_allows_smoke_and_metro(monkeypatch):
    monkeypatch.setenv("INGEST_SCOPE", "smoke")
    assert_dev_scope()
    monkeypatch.setenv("INGEST_SCOPE", "metro_10")
    assert_dev_scope()


def test_assert_dev_scope_raises_on_national(monkeypatch):
    monkeypatch.setenv("INGEST_SCOPE", "national")
    with pytest.raises(RuntimeError, match="does not support INGEST_SCOPE=national"):
        assert_dev_scope()


def test_assert_dev_scope_defaults_to_metro(monkeypatch):
    monkeypatch.delenv("INGEST_SCOPE", raising=False)
    assert_dev_scope()
