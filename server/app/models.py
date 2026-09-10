from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NdefRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recordType: str = Field(max_length=64)
    mediaType: str | None = Field(default=None, max_length=128)
    text: str | None = Field(default=None, max_length=2048)


class ScanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    serialNumber: str = Field(min_length=1, max_length=64)
    records: list[NdefRecord] = Field(default_factory=list, max_length=16)


class ScanOut(ScanIn):
    id: int
    receivedAt: datetime
