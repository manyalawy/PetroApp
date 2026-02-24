from sqlalchemy import Column, Text, Numeric, TIMESTAMP, CheckConstraint, Index, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TransferEvent(Base):
    __tablename__ = "transfer_events"

    event_id = Column(Text, primary_key=True)
    station_id = Column(Text, nullable=False)
    amount = Column(Numeric(18, 4), nullable=False)
    status = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    ingested_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_transfer_events_amount_nonneg"),
        Index("ix_transfer_events_station_id", "station_id"),
    )
