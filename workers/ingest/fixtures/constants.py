"""Shared constants for local fixture-county ingest and scoring."""

DATA_VINTAGE = "2026-Q3"

# Placeholder dimension scores until source workers exist (design doc / research).
PLACEHOLDER_SAFETY_SCORE = 65.0
PLACEHOLDER_EDUCATION_SCORE = 70.0
PLACEHOLDER_ECONOMIC_SCORE = 60.0

# Defaults when raw inputs missing for a tract.
DEFAULT_HEALTHCARE_SCORE = 50.0
DEFAULT_ENVIRONMENT_SCORE = 50.0

# Healthcare scoring: distance decay (miles).
HOSPITAL_NEAR_MILES = 2.0
HOSPITAL_FAR_MILES = 20.0
HOSPITAL_SEARCH_RADIUS_MILES = 30.0

SCORE_WEIGHTS = {
    "healthcare": 0.25,
    "safety": 0.25,
    "education": 0.20,
    "environment": 0.15,
    "economic": 0.15,
}

# EPA AQS parameter codes: Ozone, PM2.5, SO2
EPA_PARAM_CODES = "44201,88101,42401"

# AQS daily uploads lag; end far enough back that state files are usually populated.
# Window length supports 30-day environment averages in scoring.
EPA_END_LAG_DAYS = 45
EPA_LOOKBACK_DAYS = 30

# EPA worthiness gate — below this, environment falls back to Open-Meteo.
EPA_MIN_DISTINCT_DAYS = 7

# Open-Meteo fallback (modeled US AQI at county centroid).
OPEN_METEO_LOOKBACK_DAYS = 30
SOURCE_EPA_AQS = "epa_aqs"
SOURCE_OPEN_METEO = "open_meteo"
SOURCE_CMS_HOSPITALS = "cms_hospital_general_info"
SOURCE_FBI_CDE = "fbi_cde"
SOURCE_NCES_URBAN = "nces_urban"
SOURCE_ACS_BLS = "acs_bls_laus"
SOURCE_PLACEHOLDER = "placeholder"
SOURCE_DEFAULT = "default"

# FBI CDE defaults (probe-aligned).
FBI_CDE_TARGET_AGENCIES = 5
FBI_CDE_MAX_AGENCY_DISTANCE_MILES = 15.0
FBI_CDE_CHART_OFFENSES_DEFAULT = ("HOM", "ROB", "ASS", "BUR", "LAR", "MVT", "ARS")
FBI_CDE_PERSONAL_OFFENSES = ("HOM", "ROB", "ASS")
FBI_CDE_CHART_YEARS = 10
