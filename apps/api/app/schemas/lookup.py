from typing import Literal

from pydantic import BaseModel


class LookupResponse(BaseModel):
    address_id: str
    status: Literal["cached", "computing", "ready"]
    address_normalized: str
    geoid: str | None = None
