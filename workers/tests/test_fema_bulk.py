"""FEMA bulk CSV normalize + parse unit tests."""

from __future__ import annotations

from ingest.fema.client import _normalize_csv_row, _parse_nri_csv_bytes
from ingest.fema.transform import transform_tract_features


def test_normalize_csv_row_from_tractfips():
    attrs = _normalize_csv_row(
        {
            "TRACTFIPS": "44007000100",
            "RISK_SCORE": "12.5",
            "RISK_RATNG": "Relatively Low",
            "AVLN_RISKR": "Not Applicable",
            "WFIR_RISKR": "Relatively Moderate",
        }
    )
    assert attrs["STCOFIPS"] == "44007"
    assert attrs["TRACT"] == "000100"
    assert attrs["WFIR_RISKR"] == "Relatively Moderate"


def test_parse_nri_csv_bytes_and_transform():
    csv_text = (
        "TRACTFIPS,RISK_SCORE,RISK_RATNG,EAL_SCORE,SOVI_SCORE,RESL_SCORE,WFIR_RISKR\n"
        "44007000100,10,Relatively Low,1,2,3,Relatively High\n"
        "44007000200,20,Very High,4,5,6,Very High\n"
        "05007020102,5,Very Low,1,1,1,Not Applicable\n"
    )
    rows = _parse_nri_csv_bytes(csv_text.encode("utf-8"))
    assert len(rows) == 3
    filtered = _parse_nri_csv_bytes(
        csv_text.encode("utf-8"), stcofips_filter=frozenset({"44007"})
    )
    assert len(filtered) == 2
    assert {r["STCOFIPS"] for r in filtered} == {"44007"}
    known = frozenset({"44007000100", "44007000200"})
    records = transform_tract_features(filtered, known_geoids=known)
    assert {r["geoid"] for r in records} == known
    assert any("wildfire" in r["hazards"] for r in records)
