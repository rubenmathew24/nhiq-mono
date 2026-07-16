"""Tests for CMS Timely & Effective Care transform helpers."""

from ingest.cms_timely.transform import is_ed_measure, transform_measure_row


def test_is_ed_measure_accepts_op18_and_edv():
    assert is_ed_measure("OP_18b")
    assert is_ed_measure("OP-18C")
    assert is_ed_measure("EDV")
    assert is_ed_measure("OP_18A_1")
    assert not is_ed_measure("HCP_COVID_19")


def test_transform_measure_row_parses_scores_and_benchmarks():
    row = {
        "facility_id": "040001",
        "measure_id": "OP_18b",
        "measure_name": "ED-2b",
        "score": "245",
        "sample": "1200",
        "footnote": "",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
    }
    state_benchmarks = {"OP_18B": {"score": "210"}}
    national_benchmarks = {"OP_18B": {"score": "230"}}
    out = transform_measure_row(
        row,
        provider_allowlist=frozenset({"040001"}),
        state_benchmarks=state_benchmarks,
        national_benchmarks=national_benchmarks,
    )
    assert out is not None
    assert out["cms_provider_id"] == "040001"
    assert out["measure_id"] == "OP_18b"
    assert out["score_value"] == 245.0
    assert out["score_text"] is None
    assert out["sample"] == 1200.0
    assert out["state_score"] == 210.0
    assert out["national_score"] == 230.0


def test_transform_measure_row_filters_provider_and_non_ed():
    row = {
        "facility_id": "040001",
        "measure_id": "OP_18c",
        "score": "Not Available",
    }
    assert transform_measure_row(row, provider_allowlist=frozenset({"999999"})) is None
    out = transform_measure_row(row, provider_allowlist=frozenset({"040001"}))
    assert out is not None
    assert out["score_value"] is None
    assert out["score_text"] == "Not Available"

    non_ed = {"facility_id": "040001", "measure_id": "IMM_2", "score": "95"}
    assert transform_measure_row(non_ed, provider_allowlist=frozenset({"040001"})) is None
