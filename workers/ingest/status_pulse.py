"""Mid-run national status pulses for Workbook / Log Analytics."""

from __future__ import annotations

import logging
import os
from typing import Any

from ingest.status import persist_and_log, resolve_scope_counties, resolve_scope_name

logger = logging.getLogger("ingest.status_pulse")

DEFAULT_EVERY_N = 15


def status_every_n() -> int:
    raw = (os.getenv("INGEST_STATUS_EVERY_N") or str(DEFAULT_EVERY_N)).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_EVERY_N


def emit_status_snapshot(database_url: str, *, scope: str | None = None) -> dict[str, Any] | None:
    """Persist + print INGEST_STATUS_SNAPSHOT. Never raises to callers."""
    try:
        resolved = scope or resolve_scope_name()
        counties = resolve_scope_counties(resolved, database_url=database_url)
        return persist_and_log(database_url, resolved, counties)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Status snapshot emit failed: %s", exc)
        return None


class StatusPulse:
    """Call tick() after each unit; emits every ``every_n`` completed units."""

    def __init__(
        self,
        database_url: str,
        *,
        every_n: int | None = None,
        scope: str | None = None,
    ) -> None:
        self.database_url = database_url
        self.every_n = every_n if every_n is not None else status_every_n()
        self.scope = scope
        self.count = 0

    def tick(self) -> None:
        self.count += 1
        if self.count % self.every_n == 0:
            emit_status_snapshot(self.database_url, scope=self.scope)

    def flush(self) -> None:
        """Emit if there is progress not yet pulsed at a multiple of N."""
        if self.count > 0 and self.count % self.every_n != 0:
            emit_status_snapshot(self.database_url, scope=self.scope)
