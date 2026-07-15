"""Base class for all ingestion workers."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Monorepo root .env (workers/ingest/base.py → ../../..)
_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")
load_dotenv()  # also allow CWD / container env

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
# httpx INFO logs full request URLs — API keys often sit in query strings.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class BaseIngestionWorker(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = logging.getLogger(source_name)
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL is required but missing. "
                "Set it in .env or the worker container environment "
                "(Compose: postgresql://postgres:postgres@db:5432/neighborhoodiq)."
            )

    @abstractmethod
    def fetch(self) -> None:
        """Fetch raw data from source API or file."""

    @abstractmethod
    def transform(self) -> None:
        """Clean and normalize fetched data."""

    @abstractmethod
    def load(self) -> None:
        """Write transformed data to PostgreSQL."""

    def run(self) -> None:
        start = datetime.now(timezone.utc)
        self.logger.info("Starting %s ingestion", self.source_name)
        self.fetch()
        self.transform()
        self.load()
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        self.logger.info(
            "Completed %s ingestion in %.1fs", self.source_name, elapsed
        )
