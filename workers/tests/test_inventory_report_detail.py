"""US3: prefer base-complete report-detail gaps; detail-only workers_needed."""

from __future__ import annotations

from ingest.inventory import states_needing_work, workers_needed_for_state


def _empty_base() -> dict:
    return {
        "census": {},
        "epa": {},
        "cms": {},
        "fbi": {},
        "nces": {},
        "urban": {},
        "bls": {},
    }


def test_prefer_class_a_report_detail_before_virgin():
    """AR/MA-style base-complete detail gaps before virgin CA census gap."""
    inv = {
        "by_state": {
            **{w: {} for w in ("census", "epa", "cms", "fbi", "nces", "urban", "bls")},
            "census": {"06": ["06001"]},  # virgin / base gap
            "acs": {"05": ["05007"], "25": ["25001"]},  # detail (pop) on AR, MA
            "fema": {"05": ["05007"], "48": ["48001"]},  # AR + TX detail
            "cms_timely": {},
            "scoring": {"36": ["36001"]},  # NY empty score_detail
        }
    }
    # Class A: 05, 25, 48, 36 (sorted) then class B: 06
    ordered = states_needing_work(inv, max_states=3)
    assert "06" not in ordered
    assert ordered == ["05", "25", "36"]


def test_workers_needed_detail_only_for_base_complete_state():
    inv = {
        "by_state": {
            **_empty_base(),
            "acs": {},
            "fema": {"05": ["05007"]},
            "cms_timely": {"05": ["05"]},
            "scoring": {"05": ["05007"]},
        }
    }
    assert workers_needed_for_state(inv, "05") == ["fema", "cms_timely", "scoring"]
