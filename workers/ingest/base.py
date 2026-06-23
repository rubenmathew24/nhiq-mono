"""Base class for all ingestion workers."""
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime

from dotenv import load_dotenv

load_dotenv("../../.env")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)


class BaseIngestionWorker(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = logging.getLogger(source_name)
        self.database_url = os.getenv("DATABASE_URL")

    @abstractmethod
    def fetch(self) -> None:
        """Fetch raw data from source API or file."""
        pass

    @abstractmethod
    def transform(self) -> None:
        """Clean and normalize fetched data."""
        pass

    @abstractmethod
    def load(self) -> None:
        """Write transformed data to PostgreSQL."""
        pass

    def run(self) -> None:
        start = datetime.utcnow()
        self.logger.info(f"Starting {self.source_name} ingestion")
        self.fetch()
        self.transform()
        self.load()
        elapsed = (datetime.utcnow() - start).seconds
        self.logger.info(f"Completed {self.source_name} ingestion in {elapsed}s")
