"""National ingest gap inventory — which counties/states still need each worker.

Usage:
  python -m ingest.inventory

Env:
  DATABASE_URL (required)
  ORCH_STATE_FILTER — optional comma state FIPS to limit universe
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable

from dotenv import load_dotenv

from ingest.checkpoints import (
    counties_with_acs,
    counties_with_bls,
    counties_with_census_tracts,
    counties_with_epa,
    counties_with_fbi_agencies,
    counties_with_fema_nri,
    counties_with_nces,
    counties_with_score_detail,
    counties_with_urban,
    states_with_hospitals,
    states_with_timely_measures,
)
from ingest.fixtures.constants import DATA_VINTAGE
from ingest.geo.jurisdictions import INCLUDED_STATE_FIPS, STATE_FIPS_TO_ABBR
from ingest.geo.scope import (
    IncompleteNationalRegistryError,
    parse_state_batch,
    require_complete_national_registry,
)

load_dotenv()

logger = logging.getLogger("ingest.inventory")

# Pipeline order for orchestrator (geo registry assumed already loaded).
PIPELINE_WORKERS: tuple[str, ...] = (
    "census",
    "epa",
    "cms",
    "fbi",
    "nces",
    "urban",
    "acs",
    "bls",
    "fema",
    "cms_timely",
    "scoring",
)

# Base ingest (no report-detail) — used for class-A preference.
BASE_WORKERS: tuple[str, ...] = (
    "census",
    "epa",
    "cms",
    "fbi",
    "nces",
    "urban",
    "bls",
)

# Report-detail / expand stages (prefer these gaps after base is done).
DETAIL_WORKERS: tuple[str, ...] = (
    "acs",
    "fema",
    "cms_timely",
    "scoring",
)

WORKER_ACA_JOB: dict[str, str] = {
    "census": "niq-worker-census",
    "epa": "niq-worker-epa",
    "cms": "niq-worker-cms",
    "fbi": "niq-worker-fbi",
    "nces": "niq-worker-nces",
    "urban": "niq-worker-urban",
    "acs": "niq-worker-acs",
    "bls": "niq-worker-bls",
    "fema": "niq-worker-fema",
    "cms_timely": "niq-worker-cms-timely",
    "scoring": "niq-worker-scoring",
}


def _filter_counties(
    counties: frozenset[str], state_filter: frozenset[str] | None
) -> frozenset[str]:
    if not state_filter:
        return counties
    return frozenset(c for c in counties if c[:2] in state_filter)


def _group_by_state(counties: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for cf in counties:
        out.setdefault(cf[:2], []).append(cf)
    for sf in out:
        out[sf].sort()
    return dict(sorted(out.items()))


def build_inventory(
    database_url: str,
    *,
    state_filter: frozenset[str] | None = None,
    done_fns: dict[str, Callable[..., set[str]]] | None = None,
    data_vintage: str | None = None,
) -> dict[str, Any]:
    """
    Return gap inventory for national universe.

    gaps[worker] = sorted missing county FIPS (or state FIPS for cms / cms_timely).
    by_state[worker][state_fips] = missing units in that state.
    """
    vintage = data_vintage or DATA_VINTAGE
    # Full national inventory requires a complete 50+DC registry (fail closed).
    # state_filter only narrows which gaps are reported after that check.
    universe = require_complete_national_registry(database_url)
    universe = _filter_counties(universe, state_filter)
    county_list = sorted(universe)

    def _scoring_done(url: str, counties: list[str]) -> set[str]:
        return counties_with_score_detail(url, counties, data_vintage=vintage)

    fns: dict[str, Callable[..., set[str]]] = done_fns or {
        "census": counties_with_census_tracts,
        "epa": counties_with_epa,
        "fbi": counties_with_fbi_agencies,
        "nces": counties_with_nces,
        "urban": counties_with_urban,
        "acs": counties_with_acs,
        "bls": counties_with_bls,
        "fema": counties_with_fema_nri,
        "scoring": _scoring_done,
    }

    gaps: dict[str, list[str]] = {}
    by_state: dict[str, dict[str, list[str]]] = {}

    for worker in (
        "census",
        "epa",
        "fbi",
        "nces",
        "urban",
        "acs",
        "bls",
        "fema",
        "scoring",
    ):
        done = fns[worker](database_url, county_list) if county_list else set()
        missing = sorted(set(county_list) - done)
        gaps[worker] = missing
        by_state[worker] = _group_by_state(missing)

    # CMS + CMS Timely — state grain (USPS abbr in hospitals table)
    states = sorted({c[:2] for c in county_list} | (set(state_filter or ())))
    states = [s for s in states if s in INCLUDED_STATE_FIPS]
    abbrs = [STATE_FIPS_TO_ABBR[s] for s in states if s in STATE_FIPS_TO_ABBR]
    have_hospitals = states_with_hospitals(database_url, abbrs) if abbrs else set()
    cms_missing_states = sorted(
        s for s in states if STATE_FIPS_TO_ABBR.get(s) not in have_hospitals
    )
    gaps["cms"] = cms_missing_states
    by_state["cms"] = {s: [s] for s in cms_missing_states}

    have_timely = (
        states_with_timely_measures(database_url, abbrs, data_vintage=vintage)
        if abbrs
        else set()
    )
    timely_missing_states = sorted(
        s for s in states if STATE_FIPS_TO_ABBR.get(s) not in have_timely
    )
    gaps["cms_timely"] = timely_missing_states
    by_state["cms_timely"] = {s: [s] for s in timely_missing_states}

    summary = {w: len(gaps.get(w, [])) for w in PIPELINE_WORKERS}
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "universe_county_count": len(county_list),
        "state_filter": sorted(state_filter) if state_filter else None,
        "data_vintage": vintage,
        "gaps": gaps,
        "by_state": by_state,
        "summary": summary,
    }


def _state_has_worker_gap(
    by_state: dict[str, dict[str, list[str]]], state_fips: str, workers: tuple[str, ...]
) -> bool:
    for worker in workers:
        if (by_state.get(worker) or {}).get(state_fips):
            return True
    return False


def states_needing_work(
    inventory: dict[str, Any],
    *,
    max_states: int | None = None,
    force_states: frozenset[str] | None = None,
    exclude_states: frozenset[str] | None = None,
    exclusive: bool = False,
) -> list[str]:
    """Ordered list of state FIPS to process this orchestrator run.

    When ``force_states`` is non-empty: only those FIPS (sorted), capped by
    ``max_states`` — never pad with other gap states.

    When ``exclusive`` is true and force is empty: only gap states already in
    the inventory (caller scoped inventory via state_filter); still capped by
    ``max_states``.

    When neither force nor exclusive: prefer class A (base-complete,
    report-detail gaps only), then class B (other gaps), capped by
    ``max_states``.

    ``exclude_states`` drops FIPS from the ordered list before the
    ``max_states`` slice so blacklisted states do not consume the quota.
    FIPS also listed in ``force_states`` are kept (force overrides exclude).
    """
    by_state: dict[str, dict[str, list[str]]] = inventory.get("by_state") or {}
    needed: set[str] = set()
    for worker in PIPELINE_WORKERS:
        needed.update((by_state.get(worker) or {}).keys())
    force = frozenset(force_states or ())
    exclude = frozenset(exclude_states or ())

    if force:
        ordered = sorted(force)
    elif exclusive:
        ordered = sorted(needed)
    else:
        class_a = sorted(
            s
            for s in needed
            if not _state_has_worker_gap(by_state, s, BASE_WORKERS)
            and _state_has_worker_gap(by_state, s, DETAIL_WORKERS)
        )
        class_b = sorted(s for s in needed if s not in set(class_a))
        ordered = class_a + class_b

    if exclude:
        ordered = [s for s in ordered if s in force or s not in exclude]

    if max_states is not None and max_states >= 0:
        return ordered[:max_states]
    return ordered


def workers_needed_for_state(
    inventory: dict[str, Any],
    state_fips: str,
    *,
    force: bool = False,
) -> list[str]:
    """Pipeline-ordered workers that still have gaps in this state.

    When ``force`` is true, return the full pipeline (ignore gaps).
    """
    if force:
        return list(PIPELINE_WORKERS)
    by_state: dict[str, dict[str, list[str]]] = inventory.get("by_state") or {}
    out: list[str] = []
    for worker in PIPELINE_WORKERS:
        gaps = (by_state.get(worker) or {}).get(state_fips) or []
        if gaps:
            out.append(worker)
    return out


def main() -> int:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    )
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL is required")
        return 1
    state_filter = parse_state_batch(os.getenv("ORCH_STATE_FILTER"))
    try:
        inv = build_inventory(database_url, state_filter=state_filter)
    except Exception as exc:  # noqa: BLE001
        logger.error("%s", exc)
        return 1
    print(json.dumps(inv, separators=(",", ":")))
    logger.info("Inventory summary %s", inv["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
