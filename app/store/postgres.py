from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.store.base import AbstractTransferStore
from app.schemas.transfer_event import (
    TransferEventIn,
    BatchTransferResponse,
    StationSummaryResponse,
)


class PostgresTransferStore(AbstractTransferStore):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ingest_batch(
        self, events: list[TransferEventIn]
    ) -> BatchTransferResponse:
        inserted = 0
        for event in events:
            result = await self.session.execute(
                text(
                    """
                    INSERT INTO transfer_events
                        (event_id, station_id, amount, status, created_at)
                    VALUES
                        (:event_id, :station_id, :amount, :status, :created_at)
                    ON CONFLICT (event_id) DO NOTHING
                    """
                ),
                {
                    "event_id": event.event_id,
                    "station_id": event.station_id,
                    "amount": event.amount,
                    "status": event.status,
                    "created_at": event.created_at,
                },
            )
            inserted += result.rowcount
        await self.session.commit()
        return BatchTransferResponse(
            inserted=inserted,
            duplicates=len(events) - inserted,
        )

    async def get_station_summary(
        self, station_id: str
    ) -> StationSummaryResponse | None:
        result = await self.session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS events_count,
                    COALESCE(
                        SUM(amount) FILTER (WHERE status = 'approved'), 0
                    ) AS total_approved_amount
                FROM transfer_events
                WHERE station_id = :station_id
                """
            ),
            {"station_id": station_id},
        )
        row = result.fetchone()
        if row is None or row.events_count == 0:
            return None
        return StationSummaryResponse(
            station_id=station_id,
            total_approved_amount=float(row.total_approved_amount),
            events_count=row.events_count,
        )
