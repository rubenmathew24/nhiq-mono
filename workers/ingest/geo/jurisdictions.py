"""US jurisdiction FIPS for national ingest (50+DC; territories extensible)."""

from __future__ import annotations

# 50 states + District of Columbia. Append territory codes later by moving them
# from TERRITORY_STATE_FIPS into INCLUDED_STATE_FIPS (no redesign).
INCLUDED_STATE_FIPS: frozenset[str] = frozenset(
    {
        "01",  # AL
        "02",  # AK
        "04",  # AZ
        "05",  # AR
        "06",  # CA
        "08",  # CO
        "09",  # CT
        "10",  # DE
        "11",  # DC
        "12",  # FL
        "13",  # GA
        "15",  # HI
        "16",  # ID
        "17",  # IL
        "18",  # IN
        "19",  # IA
        "20",  # KS
        "21",  # KY
        "22",  # LA
        "23",  # ME
        "24",  # MD
        "25",  # MA
        "26",  # MI
        "27",  # MN
        "28",  # MS
        "29",  # MO
        "30",  # MT
        "31",  # NE
        "32",  # NV
        "33",  # NH
        "34",  # NJ
        "35",  # NM
        "36",  # NY
        "37",  # NC
        "38",  # ND
        "39",  # OH
        "40",  # OK
        "41",  # OR
        "42",  # PA
        "44",  # RI
        "45",  # SC
        "46",  # SD
        "47",  # TN
        "48",  # TX
        "49",  # UT
        "50",  # VT
        "51",  # VA
        "53",  # WA
        "54",  # WV
        "55",  # WI
        "56",  # WY
    }
)

# Not included in v1 national universe — document for easy enablement later.
TERRITORY_STATE_FIPS: frozenset[str] = frozenset(
    {
        "60",  # AS
        "66",  # GU
        "69",  # MP
        "72",  # PR
        "78",  # VI
    }
)

# Full USPS map for included + territories (CMS / FBI labels).
STATE_FIPS_TO_ABBR: dict[str, str] = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
    "60": "AS",
    "66": "GU",
    "69": "MP",
    "72": "PR",
    "78": "VI",
}
