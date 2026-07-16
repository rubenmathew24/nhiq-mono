"""Unit tests for checkpoint skip logging helpers (no DB)."""

from __future__ import annotations

import logging

from ingest.checkpoints import log_skip


def test_log_skip_emits_message(caplog):
    logger = logging.getLogger("test.checkpoints")
    with caplog.at_level(logging.INFO, logger="test.checkpoints"):
        log_skip(logger, "census", skipped=3, remaining=2)
    assert "skip_checkpoint" in caplog.text
    assert "skipped=3" in caplog.text
    assert "remaining=2" in caplog.text
