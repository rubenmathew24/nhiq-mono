"""National ingest orchestrator — inventory gaps, start only needed ACA jobs.

Usage:
  python -m ingest.orchestrate.run

Env: DATABASE_URL, AZURE_*, ORCH_MAX_STATE_UNITS, ORCH_STATE_FILTER,
     ORCH_FORCE_STATES, ORCH_STATE_EXCLUDE, ORCH_CONTINUOUS, ORCH_BATCH_STATES,
     ORCH_TIME_BUDGET_SECONDS
"""

from __future__ import annotations

import logging
import os
import sys
import time

from dotenv import load_dotenv

from ingest.geo.scope import parse_state_batch
from ingest.inventory import (
    PIPELINE_WORKERS,
    WORKER_ACA_JOB,
    build_inventory,
    states_needing_work,
    workers_needed_for_state,
)
from ingest.orchestrate.azure_jobs import AzureJobClient, client_from_env
from ingest.status_pulse import emit_status_snapshot

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger("ingest.orchestrate")


def _max_states() -> int:
    raw = (os.getenv("ORCH_MAX_STATE_UNITS") or "5").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 5


def _batch_states() -> int:
    raw = (os.getenv("ORCH_BATCH_STATES") or "10").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 10


def _time_budget_seconds() -> float:
    raw = (os.getenv("ORCH_TIME_BUDGET_SECONDS") or "20700").strip()
    try:
        return max(60.0, float(raw))
    except ValueError:
        return 20700.0


def _continuous_enabled() -> bool:
    raw = (os.getenv("ORCH_CONTINUOUS") or "0").strip().lower()
    return raw in ("1", "true", "yes")


def run_worker_once(
    client: AzureJobClient,
    worker: str,
    state_batch: str,
    *,
    force: bool = False,
    retries: int = 1,
) -> str:
    job_name = WORKER_ACA_JOB[worker]
    client.set_national_batch(job_name, state_batch, force=force)
    last_status = "Failed"
    for attempt in range(retries + 1):
        execution = client.start_job(job_name)
        last_status = client.wait_execution(job_name, execution)
        if last_status == "Succeeded":
            return last_status
        logger.warning(
            "Worker %s state=%s attempt=%s status=%s",
            worker,
            state_batch,
            attempt + 1,
            last_status,
        )
    return last_status


def run_status_emit(database_url: str) -> None:
    """In-process national status snapshot (Workbook Log Analytics line)."""
    os.environ.setdefault("INGEST_SCOPE", "national")
    emit_status_snapshot(database_url, scope="national")


def _safe_status(database_url: str, context: str) -> None:
    try:
        run_status_emit(database_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Status refresh (%s): %s", context, exc)


def _inventory_has_gaps(
    inv: dict,
    *,
    force_states: frozenset[str],
    exclude_states: frozenset[str],
    exclusive: bool,
) -> bool:
    states = states_needing_work(
        inv,
        max_states=None,
        force_states=force_states,
        exclude_states=exclude_states,
        exclusive=exclusive,
    )
    return bool(states)


def _run_bounded_pass(
    client: AzureJobClient,
    database_url: str,
    *,
    inv: dict,
    states: list[str],
    force_states: frozenset[str],
    started: float,
    time_budget: float,
) -> tuple[bool, bool]:
    """Process states either one-by-one (bounded) or batched (continuous callers).

    Returns (hard_fail, budget_hit).
    """
    hard_fail = False
    continuous = _continuous_enabled()
    batch_size = _batch_states() if continuous else 1

    if continuous:
        # Per-worker: batch up to ORCH_BATCH_STATES gap states into one execution.
        for worker in PIPELINE_WORKERS:
            if time.monotonic() - started >= time_budget:
                logger.info("orch_time_budget_hit before worker=%s", worker)
                return hard_fail, True

            needing: list[str] = []
            for state_fips in states:
                forcing = state_fips in force_states
                needed = workers_needed_for_state(inv, state_fips, force=forcing)
                if worker in needed:
                    needing.append(state_fips)

            while needing:
                if time.monotonic() - started >= time_budget:
                    logger.info(
                        "orch_time_budget_hit worker=%s remaining_states=%s",
                        worker,
                        len(needing),
                    )
                    return hard_fail, True

                batch = needing[:batch_size]
                needing = needing[batch_size:]
                batch_csv = ",".join(batch)
                # Force only when every state in the batch is forced.
                forcing = all(s in force_states for s in batch) and bool(batch)
                gap_total = 0
                for s in batch:
                    gaps = (inv.get("by_state") or {}).get(worker, {}).get(s) or []
                    gap_total += len(gaps)
                logger.info(
                    "orch_start worker=%s state=%s gap_count=%s force=%s",
                    worker,
                    batch_csv,
                    gap_total if not forcing else "all",
                    forcing,
                )
                try:
                    status = run_worker_once(
                        client,
                        worker,
                        batch_csv,
                        force=forcing,
                        retries=1 if worker == "fbi" else 0,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "orch_error worker=%s state=%s err=%s",
                        worker,
                        batch_csv,
                        exc,
                    )
                    hard_fail = True
                    _safe_status(database_url, "after worker error")
                    continue
                if status != "Succeeded":
                    logger.warning(
                        "orch_incomplete worker=%s state=%s status=%s",
                        worker,
                        batch_csv,
                        status,
                    )
                    if worker not in ("fbi",):
                        hard_fail = True
                _safe_status(database_url, f"after {worker} {batch_csv}")
        return hard_fail, False

    # Bounded legacy path: one state × one worker at a time.
    for state_fips in states:
        if time.monotonic() - started >= time_budget:
            logger.info("orch_time_budget_hit state=%s", state_fips)
            return hard_fail, True
        forcing = state_fips in force_states
        workers = workers_needed_for_state(inv, state_fips, force=forcing)
        logger.info("State %s workers=%s force=%s", state_fips, workers, forcing)
        for worker in workers:
            if time.monotonic() - started >= time_budget:
                logger.info(
                    "orch_time_budget_hit worker=%s state=%s", worker, state_fips
                )
                return hard_fail, True
            gaps = (inv.get("by_state") or {}).get(worker, {}).get(state_fips) or []
            if not forcing and not gaps:
                logger.info(
                    "orch_skip worker=%s state=%s reason=no_gaps",
                    worker,
                    state_fips,
                )
                continue
            logger.info(
                "orch_start worker=%s state=%s gap_count=%s force=%s",
                worker,
                state_fips,
                len(gaps) if not forcing else "all",
                forcing,
            )
            try:
                status = run_worker_once(
                    client,
                    worker,
                    state_fips,
                    force=forcing,
                    retries=1 if worker == "fbi" else 0,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "orch_error worker=%s state=%s err=%s", worker, state_fips, exc
                )
                hard_fail = True
                _safe_status(database_url, "after worker error")
                continue
            if status != "Succeeded":
                logger.warning(
                    "orch_incomplete worker=%s state=%s status=%s",
                    worker,
                    state_fips,
                    status,
                )
                if worker not in ("fbi",):
                    hard_fail = True
            _safe_status(database_url, f"after {worker} {state_fips}")
    return hard_fail, False


def run() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    state_filter = parse_state_batch(os.getenv("ORCH_STATE_FILTER"))
    force_states = parse_state_batch(os.getenv("ORCH_FORCE_STATES")) or frozenset()
    exclude_states = parse_state_batch(os.getenv("ORCH_STATE_EXCLUDE")) or frozenset()
    continuous = _continuous_enabled()
    max_states = None if continuous else _max_states()
    time_budget = _time_budget_seconds()
    client = client_from_env()
    started = time.monotonic()
    exclusive = bool(force_states) or bool(state_filter)

    logger.info(
        "orch_mode continuous=%s batch_states=%s time_budget=%s max_states=%s",
        continuous,
        _batch_states() if continuous else 1,
        int(time_budget),
        max_states,
    )

    hard_fail = False
    while True:
        inv = build_inventory(database_url, state_filter=state_filter)
        logger.info("Inventory summary %s", inv["summary"])
        if force_states:
            logger.info("Force states=%s", sorted(force_states))
        if exclude_states:
            logger.info("Exclude states=%s", sorted(exclude_states))
            overridden = sorted(force_states & exclude_states)
            if overridden:
                logger.info("Force overrides exclude for states=%s", overridden)

        states = states_needing_work(
            inv,
            max_states=max_states,
            force_states=force_states,
            exclude_states=exclude_states,
            exclusive=exclusive,
        )
        if not states:
            logger.info("No gaps for selected universe — nothing to start")
            _safe_status(database_url, "no gaps")
            logger.info("orch_cycle_result=complete")
            return 0 if not hard_fail else 1

        logger.info(
            "Will process states=%s (max=%s continuous=%s)",
            states,
            max_states if max_states is not None else "unlimited",
            continuous,
        )

        pass_hard, budget_hit = _run_bounded_pass(
            client,
            database_url,
            inv=inv,
            states=states,
            force_states=force_states,
            started=started,
            time_budget=time_budget,
        )
        hard_fail = hard_fail or pass_hard

        inv2 = build_inventory(database_url, state_filter=state_filter)
        logger.info("Final inventory summary %s", inv2["summary"])
        summary = inv2.get("summary") or {}
        logger.info("national_progress %s", summary)
        _safe_status(database_url, "end of cycle")

        still_gaps = _inventory_has_gaps(
            inv2,
            force_states=force_states,
            exclude_states=exclude_states,
            exclusive=exclusive,
        )
        if not still_gaps:
            logger.info("orch_cycle_result=complete")
            return 0 if not hard_fail else 1

        if not continuous:
            # Bounded mode: one pass only.
            logger.info("orch_cycle_result=more_work")
            return 1 if hard_fail else 0

        if budget_hit or (time.monotonic() - started >= time_budget):
            logger.info("orch_cycle_result=more_work")
            return 2 if not hard_fail else 1

        logger.info("orch_cycle_continue gaps_remain=1")


def main() -> int:
    try:
        return run()
    except Exception as exc:  # noqa: BLE001
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
