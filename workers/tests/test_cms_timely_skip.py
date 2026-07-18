"""CMS Timely skip-done unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ingest.cms_timely.run import CmsTimelyWorker


def test_cms_timely_skips_fetch_when_states_done(monkeypatch):
    monkeypatch.setenv("INGEST_FORCE", "0")
    worker = CmsTimelyWorker()
    worker.database_url = "postgresql://test"
    worker.logger = MagicMock()

    with patch(
        "ingest.cms_timely.run.active_state_abbrs", return_value=frozenset({"RI", "MA"})
    ):
        with patch(
            "ingest.cms_timely.run.states_with_timely_measures",
            return_value={"RI", "MA"},
        ):
            with patch(
                "ingest.cms_timely.run.discover_timely_dataset_ids"
            ) as discover:
                worker.fetch()

    assert worker._states == frozenset()
    assert worker._raw_pages == []
    discover.assert_not_called()
