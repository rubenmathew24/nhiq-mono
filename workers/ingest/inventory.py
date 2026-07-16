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
    counties_with_fbi_cde_scores,
    counties_with_nces,
    counties_with_urban,
    states_with_hospitals,
)
from ingest.geo.jurisdictions import INCLUDED_STATE_FIPS, STATE_FIPS_TO_ABBR
from ingest.geo.scope import load_national_universe_counties, parse_state_batch

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
    done_fns: dict[str, Callable[[str, list[str]], set[str]]] | None = None,
) -> dict[str, Any]:
    """
    Return gap inventory for national universe.

    gaps[worker] = sorted missing county FIPS (or state FIPS for cms).
    by_state[worker][state_fips] = missing units in that state.
    """
    universe = load_national_universe_counties(database_url)
    universe = _filter_counties(universe, state_filter)
    county_list = sorted(universe)

    fns = done_fns or {
        "census": counties_with_census_tracts,
        "epa": counties_with_epa,
        "fbi": counties_with_fbi_agencies,
        "nces": counties_with_nces,
        "urban": counties_with_urban,
        "acs": counties_with_acs,
        "bls": counties_with_bls,
        "scoring": counties_with_fbi_cde_scores,
    }

    gaps: dict[str, list[str]] = {}
    by_state: dict[str, dict[str, list[str]]] = {}

    for worker in ("census", "epa", "fbi", "nces", "urban", "acs", "bls", "scoring"):
        done = fns[worker](database_url, county_list) if county_list else set()
        missing = sorted(set(county_list) - done)
        gaps[worker] = missing
        by_state[worker] = _group_by_state(missing)

    # CMS — state grain (USPS abbr in hospitals table)
    states = sorted({c[:2] for c in county_list} | (set(state_filter or ())))
    states = [s for s in states if s in INCLUDED_STATE_FIPS]
    abbrs = [STATE_FIPS_TO_ABBR[s] for s in states if s in STATE_FIPS_TO_ABBR]
    have = states_with_hospitals(database_url, abbrs) if abbrs else set()
    cms_missing_states = sorted(
        s for s in states if STATE_FIPS_TO_ABBR.get(s) not in have
    )
    gaps["cms"] = cms_missing_states
    by_state["cms"] = {s: [s] for s in cms_missing_states}

    summary = {w: len(gaps.get(w, [])) for w in PIPELINE_WORKERS}
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "universe_county_count": len(county_list),
        "state_filter": sorted(state_filter) if state_filter else None,
        "gaps": gaps,
        "by_state": by_state,
        "summary": summary,
    }


def states_needing_work(
    inventory: dict[str, Any],
    *,
    max_states: int | None = None,
    force_states: frozenset[str] | None = None,
    exclusive: bool = False,
) -> list[str]:
    """Ordered list of state FIPS to process this orchestrator run.

    When ``force_states`` is non-empty: only those FIPS (sorted), capped by
    ``max_states`` — never pad with other gap states.

    When ``exclusive`` is true and force is empty: only gap states already in
    the inventory (caller scoped inventory via state_filter); still capped by
    ``max_states``.

    When neither force nor exclusive: forced (if any) first, then remaining
    gap states, capped by ``max_states`` (unscoped national continue).
    """
    by_state: dict[str, dict[str, list[str]]] = inventory.get("by_state") or {}
    needed: set[str] = set()
    for worker in PIPELINE_WORKERS:
        needed.update((by_state.get(worker) or {}).keys())
    force = frozenset(force_states or ())

    if force:
        ordered = sorted(force)
    elif exclusive:
        ordered = sorted(needed)
    else:
        ordered = sorted(force) + sorted(needed - force)

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
