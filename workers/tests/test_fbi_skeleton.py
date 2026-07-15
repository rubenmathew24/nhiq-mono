"""FBI worker entrypoint fails clearly without API key."""

import os
from unittest.mock import patch

from ingest.fbi.run import main


def test_fbi_main_fails_without_api_key():
    with patch.dict(os.environ, {"FBI_CDE_API_KEY": "", "DATABASE_URL": "postgresql://x"}, clear=False):
        # Clear key explicitly even if host .env loaded something.
        os.environ.pop("FBI_CDE_API_KEY", None)
        # BaseIngestionWorker requires DATABASE_URL; provide dummy.
        os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5433/neighborhoodiq"
        with patch("ingest.fbi.client.require_api_key", side_effect=RuntimeError("FBI_CDE_API_KEY is required")):
            code = main()
    assert code == 1
