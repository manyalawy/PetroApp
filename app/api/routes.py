import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.transfer_event import (
    BatchTransferRequest,
    BatchTransferResponse,
    StationSummaryResponse,
)
from app.services.transfer_service import TransferService
from app.store.postgres import PostgresTransferStore

logger = logging.getLogger(__name__)
router = APIRouter()


def get_service(session: AsyncSession = Depends(get_session)) -> TransferService:
    return TransferService(PostgresTransferStore(session))


@router.post("/transfers", response_model=BatchTransferResponse, status_code=201)
async def post_transfers(
    body: BatchTransferRequest,
    service: TransferService = Depends(get_service),
) -> BatchTransferResponse:
    logger.info("Ingesting batch of %d events", len(body.events))
    result = await service.ingest_batch(body.events)
    logger.info("Inserted=%d duplicates=%d", result.inserted, result.duplicates)
    return result


@router.get(
    "/stations/{station_id}/summary",
    response_model=StationSummaryResponse,
)
async def get_station_summary(
    station_id: str,
    service: TransferService = Depends(get_service),
) -> StationSummaryResponse:
    summary = await service.get_station_summary(station_id)
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail=f"No events found for station '{station_id}'",
        )
    return summary
