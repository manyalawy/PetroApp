from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class TransferEventIn(BaseModel):
    event_id: str
    station_id: str
    amount: float = Field(ge=0)
    status: str
    created_at: datetime

    @field_validator("event_id", "station_id", "status")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v


class BatchTransferRequest(BaseModel):
    events: list[TransferEventIn]


class BatchTransferResponse(BaseModel):
    inserted: int
    duplicates: int


class StationSummaryResponse(BaseModel):
    station_id: str
    total_approved_amount: float
    events_count: int
