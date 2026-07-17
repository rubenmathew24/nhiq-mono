"""Scope: FEMA/CMS Timely allow national with batch; refuse without batch."""

from __future__ import annotations

import pytest

from ingest.geo.scope import assert_dev_scope, require_national_state_batch, resolve_ingest_scope


def test_assert_dev_scope_still_documents_legacy_refuse(monkeypatch):
    """Helper remains for any remaining callers; workers no longer use it."""
    monkeypatch.setenv("INGEST_SCOPE", "smoke")
    assert_dev_scope()
    monkeypatch.setenv("INGEST_SCOPE", "national")
    with pytest.raises(RuntimeError, match="does not support INGEST_SCOPE=national"):
        assert_dev_scope()


def test_resolve_allows_national(monkeypatch):
    monkeypatch.setenv("INGEST_SCOPE", "national")
    assert resolve_ingest_scope() == "national"


def test_national_requires_state_batch(monkeypatch):
    monkeypatch.setenv("INGEST_SCOPE", "national")
    monkeypatch.delenv("INGEST_STATE_BATCH", raising=False)
    with pytest.raises(RuntimeError, match="INGEST_STATE_BATCH"):
        require_national_state_batch()


def test_national_batch_parses(monkeypatch):
    monkeypatch.setenv("INGEST_SCOPE", "national")
    monkeypatch.setenv("INGEST_STATE_BATCH", "05,25")
    assert require_national_state_batch() == frozenset({"05", "25"})


def test_fema_module_no_longer_imports_assert_dev_scope():
    import ingest.fema.run as fema_run
    import inspect

    src = inspect.getsource(fema_run)
    assert "assert_dev_scope" not in src


def test_cms_timely_module_no_longer_imports_assert_dev_scope():
    import ingest.cms_timely.run as timely_run
    import inspect

    src = inspect.getsource(timely_run)
    assert "assert_dev_scope" not in src
