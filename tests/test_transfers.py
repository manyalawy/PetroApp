import asyncio

from httpx import AsyncClient

BASE_EVENT = {
    "event_id": "evt-001",
    "station_id": "S1",
    "amount": 100.0,
    "status": "approved",
    "created_at": "2026-02-19T10:00:00Z",
}


def make_event(**kwargs) -> dict:
    return {**BASE_EVENT, **kwargs}


# ── Test 1: Batch insert returns correct inserted/duplicates ──────────────────

async def test_batch_insert_counts(client: AsyncClient):
    events = [
        make_event(event_id="evt-001"),
        make_event(event_id="evt-002"),
        make_event(event_id="evt-001"),  # duplicate within same batch
    ]
    resp = await client.post("/transfers", json={"events": events})
    assert resp.status_code == 201
    data = resp.json()
    assert data["inserted"] == 2
    assert data["duplicates"] == 1


# ── Test 2: Duplicate event doesn't change totals ─────────────────────────────

async def test_duplicate_doesnt_change_totals(client: AsyncClient):
    payload = {"events": [make_event(event_id="evt-001", amount=100.0)]}
    await client.post("/transfers", json=payload)
    await client.post("/transfers", json=payload)  # second send — duplicate

    resp = await client.get("/stations/S1/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_approved_amount"] == 100.0
    assert data["events_count"] == 1


# ── Test 3: Out-of-order arrival produces same totals ─────────────────────────

async def test_out_of_order_same_totals(client: AsyncClient):
    events = [
        make_event(event_id="evt-003", amount=50.0,  created_at="2026-02-19T12:00:00Z"),
        make_event(event_id="evt-001", amount=25.0,  created_at="2026-02-19T08:00:00Z"),
        make_event(event_id="evt-002", amount=75.0,  created_at="2026-02-19T10:00:00Z"),
    ]
    resp = await client.post("/transfers", json={"events": events})
    assert resp.status_code == 201

    resp = await client.get("/stations/S1/summary")
    assert resp.json()["total_approved_amount"] == 150.0


# ── Test 4: Concurrent ingestion of same IDs doesn't double count ─────────────

async def test_concurrent_no_double_insert(client: AsyncClient):
    payload = {"events": [make_event(event_id="evt-001", amount=100.0)]}

    results = await asyncio.gather(
        client.post("/transfers", json=payload),
        client.post("/transfers", json=payload),
        client.post("/transfers", json=payload),
    )

    total_inserted = sum(r.json()["inserted"] for r in results if r.status_code == 201)
    assert total_inserted == 1

    resp = await client.get("/stations/S1/summary")
    data = resp.json()
    assert data["total_approved_amount"] == 100.0
    assert data["events_count"] == 1


# ── Test 5: Summary correctness per station (only approved totals) ─────────────

async def test_summary_per_station(client: AsyncClient):
    await client.post("/transfers", json={"events": [
        make_event(event_id="s1-a", station_id="S1", amount=100.0, status="approved"),
        make_event(event_id="s1-b", station_id="S1", amount=50.0,  status="pending"),  # not summed
        make_event(event_id="s2-a", station_id="S2", amount=200.0, status="approved"),
    ]})

    s1 = (await client.get("/stations/S1/summary")).json()
    assert s1["total_approved_amount"] == 100.0
    assert s1["events_count"] == 2  # both events stored

    s2 = (await client.get("/stations/S2/summary")).json()
    assert s2["total_approved_amount"] == 200.0
    assert s2["events_count"] == 1


# ── Test 6: Validation failure → 400 (fail-fast) ─────────────────────────────

async def test_validation_fail_fast_missing_field(client: AsyncClient):
    # Missing event_id
    resp = await client.post("/transfers", json={"events": [
        {"station_id": "S1", "amount": 50.0, "status": "approved",
         "created_at": "2026-02-19T10:00:00Z"}
    ]})
    assert resp.status_code == 400


async def test_validation_fail_fast_negative_amount(client: AsyncClient):
    resp = await client.post("/transfers", json={"events": [make_event(amount=-1.0)]})
    assert resp.status_code == 400


async def test_station_not_found_returns_404(client: AsyncClient):
    resp = await client.get("/stations/NONEXISTENT/summary")
    assert resp.status_code == 404
