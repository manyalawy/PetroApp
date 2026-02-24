from abc import ABC, abstractmethod
from app.schemas.transfer_event import (
    TransferEventIn,
    BatchTransferResponse,
    StationSummaryResponse,
)


class AbstractTransferStore(ABC):
    @abstractmethod
    async def ingest_batch(
        self, events: list[TransferEventIn]
    ) -> BatchTransferResponse: ...

    @abstractmethod
    async def get_station_summary(
        self, station_id: str
    ) -> StationSummaryResponse | None: ...
