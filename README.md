# PetroApp — Station Transfers Service

A FastAPI service that ingests station transfer events (idempotent + concurrency-safe) and exposes per-station reconciliation summaries.

## Tech Stack

- Python 3.12, FastAPI, SQLAlchemy 2 (async), asyncpg
- PostgreSQL 16
- pytest + httpx
- Docker + docker-compose

## Requirements (local)

- Python 3.12+
- Docker (for Postgres)

## Run Locally

```bash
# Install dependencies
pip install -e ".[test]"

# Start Postgres
docker compose up db -d

# Run app
make run
# OR: uvicorn app.main:app --reload
```

Service available at: http://localhost:8000
Swagger UI: http://localhost:8000/docs
OpenAPI JSON: http://localhost:8000/openapi.json

## Run with Docker

```bash
docker compose up --build
```

## Run Tests

```bash
# Local (requires Postgres running)
docker compose up db -d
make test
# OR: pytest tests/ -v

# Docker
docker compose run --rm app pytest tests/ -v
```

## API Examples

### POST /transfers

```bash
curl -X POST http://localhost:8000/transfers \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_id": "evt-001",
        "station_id": "S1",
        "amount": 100.50,
        "status": "approved",
        "created_at": "2026-02-19T10:00:00Z"
      },
      {
        "event_id": "evt-002",
        "station_id": "S1",
        "amount": 200.00,
        "status": "approved",
        "created_at": "2026-02-19T11:00:00Z"
      }
    ]
  }'
# Response: {"inserted": 2, "duplicates": 0}
```

### GET /stations/{station_id}/summary

```bash
curl http://localhost:8000/stations/S1/summary
# Response: {"station_id": "S1", "total_approved_amount": 300.5, "events_count": 2}
```

## Design Notes

### Idempotency Strategy

`event_id` is the `PRIMARY KEY` of the `transfer_events` table. Each insert uses:

```sql
INSERT INTO transfer_events (...) VALUES (...) ON CONFLICT (event_id) DO NOTHING
```

This is atomic at the DB level — no application-level state needed.

### Concurrency Strategy

PostgreSQL's MVCC ensures that two concurrent transactions with the same `event_id` are serialized by the unique constraint. The first succeeds; the second gets `ON CONFLICT` and inserts 0 rows. No Redis, no application locks.

**Why not Redis?** Redis distributed locks are valuable for cross-service coordination, but within one service backed by Postgres, the DB constraint is simpler, cheaper, and has one fewer failure mode.

### Validation Strategy: Fail-Fast

The entire batch is validated by Pydantic before any DB write. If any event is invalid, the request returns `400` with a descriptive error. No partial inserts.

### events_count Definition

`events_count` counts **all stored events** for a station, regardless of status. Only `total_approved_amount` filters to `status = 'approved'`.

### Swappable Store

The `AbstractTransferStore` interface (`app/store/base.py`) decouples business logic from persistence. The `PostgresTransferStore` is the current adapter. To swap (e.g. to SQLite or an in-memory store for testing), implement the interface and override the `get_session` dependency.
