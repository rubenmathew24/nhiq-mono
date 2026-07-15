"""Canonical test addresses and fixture-county FIPS for local Docker ingest."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalAddress:
    address: str
    # Full county FIPS SSCCC (state + county)
    county_fips: str
    label: str
    # Approximate lat/lon for FBI CDE agency selection (fixture city points)
    latitude: float
    longitude: float
    state_abbr: str
    county_name: str


# Order matches specs/002-data-ingestion-workers/spec.md Clarifications.
CANONICAL_ADDRESSES: tuple[CanonicalAddress, ...] = (
    CanonicalAddress(
        "609 SE Jamaica Dr, Bentonville, AR 72712",
        "05007",
        "Benton County, AR",
        36.3729,
        -94.2088,
        "AR",
        "Benton",
    ),
    CanonicalAddress(
        "233 S Wacker Dr, Chicago, IL 60606",
        "17031",
        "Cook County, IL",
        41.8786,
        -87.6364,
        "IL",
        "Cook",
    ),
    CanonicalAddress(
        "350 5th Ave, New York, NY 10118",
        "36061",
        "New York County, NY",
        40.7484,
        -73.9857,
        "NY",
        "New York",
    ),
    CanonicalAddress(
        "98 San Jacinto Blvd, Austin, TX 78701",
        "48453",
        "Travis County, TX",
        30.2640,
        -97.7430,
        "TX",
        "Travis",
    ),
    CanonicalAddress(
        "400 Broad St, Seattle, WA 98109",
        "53033",
        "King County, WA",
        47.6205,
        -122.3493,
        "WA",
        "King",
    ),
    CanonicalAddress(
        "1001 Brickell Bay Dr, Miami, FL 33131",
        "12086",
        "Miami-Dade County, FL",
        25.7617,
        -80.1918,
        "FL",
        "Miami-Dade",
    ),
    CanonicalAddress(
        "1700 Broadway, Denver, CO 80202",
        "08031",
        "Denver County, CO",
        39.7531,
        -104.9885,
        "CO",
        "Denver",
    ),
    CanonicalAddress(
        "191 Peachtree St NE, Atlanta, GA 30303",
        "13121",
        "Fulton County, GA",
        33.7590,
        -84.3870,
        "GA",
        "Fulton",
    ),
    CanonicalAddress(
        "1 Market St, San Francisco, CA 94105",
        "06075",
        "San Francisco County, CA",
        37.7936,
        -122.3950,
        "CA",
        "San Francisco",
    ),
    CanonicalAddress(
        "2 N Central Ave, Phoenix, AZ 85004",
        "04013",
        "Maricopa County, AZ",
        33.4494,
        -112.0740,
        "AZ",
        "Maricopa",
    ),
)


# State FIPS → USPS abbreviation for CMS hospital state filtering.
FIPS_TO_STATE_ABBR: dict[str, str] = {
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "12": "FL",
    "13": "GA",
    "17": "IL",
    "36": "NY",
    "48": "TX",
    "53": "WA",
}


def fixture_county_fips() -> frozenset[str]:
    """Return SSCCC county FIPS for all fixture addresses."""
    return frozenset(a.county_fips for a in CANONICAL_ADDRESSES)


def fixture_state_fips() -> frozenset[str]:
    """Return distinct 2-digit state FIPS for fixture counties."""
    return frozenset(cf[:2] for cf in fixture_county_fips())


def fixture_state_abbrs() -> frozenset[str]:
    """Return USPS state codes for fixture geography (CMS filter)."""
    return frozenset(
        FIPS_TO_STATE_ABBR[sf]
        for sf in fixture_state_fips()
        if sf in FIPS_TO_STATE_ABBR
    )


def county_in_fixture(state_fips: str, county_fips: str) -> bool:
    """True if STATEFP + COUNTYFP pair is in the fixture allowlist."""
    return f"{state_fips}{county_fips}" in fixture_county_fips()
