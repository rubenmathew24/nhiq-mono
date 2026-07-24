from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"

    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    ANTHROPIC_API_KEY: str = ""
    MAPBOX_TOKEN: str = ""

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://nh-iq.com",
    ]

    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER_NAME: str = "reports"

    EPA_AQS_EMAIL: str = ""
    EPA_AQS_KEY: str = ""
    FBI_API_KEY: str = ""
    CENSUS_API_KEY: str = ""

    # Must match workers/ingest/fixtures/constants.py DATA_VINTAGE for live reports.
    SCORE_DATA_VINTAGE: str = "2026-Q3"

    class Config:
        env_file = "../../.env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
