from app.schemas.transfer_event import TransferEventIn, BatchTransferRequest


def test_valid_event_parses():
    event = TransferEventIn(
        event_id="evt-001",
        station_id="S1",
        amount=100.0,
        status="approved",
        created_at="2026-02-19T10:00:00Z",
    )
    assert event.event_id == "evt-001"


def test_negative_amount_rejected():
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):
        TransferEventIn(
            event_id="evt-001",
            station_id="S1",
            amount=-1.0,
            status="approved",
            created_at="2026-02-19T10:00:00Z",
        )
