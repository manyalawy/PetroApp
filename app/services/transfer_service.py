from app.store.base import AbstractTransferStore
from app.schemas.transfer_event import (
    TransferEventIn,
    BatchTransferResponse,
    StationSummaryResponse,
)


class TransferService:
    def __init__(self, store: AbstractTransferStore) -> None:
        self.store = store

    async def ingest_batch(
        self, events: list[TransferEventIn]
    ) -> BatchTransferResponse:
        return await self.store.ingest_batch(events)

    async def get_station_summary(
        self, station_id: str
    ) -> StationSummaryResponse | None:
        return await self.store.get_station_summary(station_id)
