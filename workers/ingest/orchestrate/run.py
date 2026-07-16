"""National ingest orchestrator — inventory gaps, start only needed ACA jobs.

Usage:
  python -m ingest.orchestrate.run

Env: DATABASE_URL, AZURE_*, ORCH_MAX_STATE_UNITS, ORCH_STATE_FILTER
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

from ingest.geo.scope import parse_state_batch
from ingest.inventory import (
    WORKER_ACA_JOB,
    build_inventory,
    states_needing_work,
    workers_needed_for_state,
)
from ingest.orchestrate.azure_jobs import AzureJobClient, client_from_env

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


def run_worker_once(
    client: AzureJobClient,
    worker: str,
    state_fips: str,
    *,
    retries: int = 1,
) -> str:
    job_name = WORKER_ACA_JOB[worker]
    client.set_national_batch(job_name, state_fips)
    last_status = "Failed"
    for attempt in range(retries + 1):
        execution = client.start_job(job_name)
        last_status = client.wait_execution(job_name, execution)
        if last_status == "Succeeded":
            return last_status
        logger.warning(
            "Worker %s state=%s attempt=%s status=%s",
            worker,
            state_fips,
            attempt + 1,
            last_status,
        )
    return last_status


def run_status(client: AzureJobClient) -> None:
    job_name = "niq-worker-status"
    client.set_env_vars(job_name, {"INGEST_SCOPE": "national"})
    execution = client.start_job(job_name)
    status = client.wait_execution(job_name, execution, timeout_seconds=900)
    logger.info("Status job finished status=%s", status)


def run() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    state_filter = parse_state_batch(os.getenv("ORCH_STATE_FILTER"))
    max_states = _max_states()
    client = client_from_env()

    inv = build_inventory(database_url, state_filter=state_filter)
    logger.info("Inventory summary %s", inv["summary"])
    states = states_needing_work(inv, max_states=max_states)
    if not states:
        logger.info("No gaps for selected universe — nothing to start")
        try:
            run_status(client)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Status refresh skipped: %s", exc)
        return 0

    logger.info("Will process states=%s (max=%s)", states, max_states)
    hard_fail = False
    for state_fips in states:
        workers = workers_needed_for_state(inv, state_fips)
        logger.info("State %s workers=%s", state_fips, workers)
        for worker in workers:
            # Re-check inventory lightly: rebuild would be expensive; trust initial
            # and rely on worker skip_checkpoint. Optionally skip if empty list.
            gaps = (inv.get("by_state") or {}).get(worker, {}).get(state_fips) or []
            if not gaps:
                logger.info(
                    "orch_skip worker=%s state=%s reason=no_gaps",
                    worker,
                    state_fips,
                )
                continue
            logger.info(
                "orch_start worker=%s state=%s gap_count=%s",
                worker,
                state_fips,
                len(gaps),
            )
            try:
                status = run_worker_once(
                    client, worker, state_fips, retries=1 if worker == "fbi" else 0
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "orch_error worker=%s state=%s err=%s", worker, state_fips, exc
                )
                hard_fail = True
                continue
            if status != "Succeeded":
                # FBI may fail-closed on partial coverage after writing some counties
                logger.warning(
                    "orch_incomplete worker=%s state=%s status=%s",
                    worker,
                    state_fips,
                    status,
                )
                if worker not in ("fbi",):
                    hard_fail = True
        try:
            run_status(client)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Status refresh after state %s: %s", state_fips, exc)

    # Final inventory summary
    inv2 = build_inventory(database_url, state_filter=state_filter)
    logger.info("Final inventory summary %s", inv2["summary"])
    return 1 if hard_fail else 0


def main() -> int:
    try:
        return run()
    except Exception as exc:  # noqa: BLE001
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
