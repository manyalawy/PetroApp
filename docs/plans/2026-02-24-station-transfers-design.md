# Station Transfers Service — Design Document

**Date:** 2026-02-24
**Status:** Approved

---

## Context

Take-home assignment: build a service that ingests station transfer events from an external system and exposes a reconciliation summary per station. The two core requirements are:
1. Safe ingestion (idempotent + concurrency-safe)
2. Accurate per-station reconciliation summary

---

## Tech Stack

- **Runtime:** Python 3.12
- **Framework:** FastAPI (async, auto-generates OpenAPI)
- **Database:** PostgreSQL 16 (via Docker)
- **ORM/Driver:** SQLAlchemy 2.x (async) + asyncpg
- **Migrations:** Alembic
- **Testing:** pytest + pytest-asyncio + httpx
- **Containers:** Docker + docker-compose

---

## Project Structure

```
PetroApp/
├── app/
│   ├── main.py                  # FastAPI app, lifespan handler
│   ├── db.py                    # Async engine + session factory
│   ├── api/
│   │   └── routes.py            # POST /transfers, GET /stations/{id}/summary
│   ├── models/
│   │   └── transfer_event.py    # SQLAlchemy ORM model
│   ├── schemas/
│   │   └── transfer_event.py    # Pydantic request/response schemas
│   ├── services/
│   │   └── transfer_service.py  # Business logic
│   └── store/
│       ├── base.py              # Abstract store interface (port/protocol)
│       └── postgres.py          # PostgreSQL implementation (adapter)
├── migrations/                  # Alembic migrations
│   └── versions/
├── tests/
│   ├── conftest.py              # DB fixtures, test client
│   └── test_transfers.py        # All required tests
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── README.md
└── pyproject.toml
```

---

## Data Model

**Table: `transfer_events`**

| Column        | Type            | Constraint                  |
|---------------|-----------------|-----------------------------|
| `event_id`    | `TEXT`          | `PRIMARY KEY`               |
| `station_id`  | `TEXT`          | `NOT NULL`, `INDEX`         |
| `amount`      | `NUMERIC(18,4)` | `NOT NULL`, `CHECK >= 0`   |
| `status`      | `TEXT`          | `NOT NULL`                  |
| `created_at`  | `TIMESTAMPTZ`   | `NOT NULL`                  |
| `ingested_at` | `TIMESTAMPTZ`   | `NOT NULL`, `DEFAULT now()` |

`event_id` as `PRIMARY KEY` enforces the unique constraint at the DB level.

---

## Idempotency & Concurrency Strategy

**Approach: DB unique constraint + `INSERT ... ON CONFLICT DO NOTHING`**

For each event in a batch:
```sql
INSERT INTO transfer_events (event_id, station_id, amount, status, created_at)
VALUES (...)
ON CONFLICT (event_id) DO NOTHING
```

- The `PRIMARY KEY` on `event_id` is a unique constraint — Postgres enforces this atomically via MVCC.
- Two concurrent requests with the same `event_id` are handled at the DB level: one succeeds, the other gets `ON CONFLICT` (zero rows affected).
- No application-level locks, no Redis, no advisory locks needed.
- Counting affected rows (`rowcount`) vs. total events gives `inserted` and `duplicates`.

**Why not Redis locking?** Redis distributed locks are valuable for cross-service coordination, but within a single service backed by Postgres, the DB constraint is simpler, atomically correct, and has no additional failure modes.

---

## API

### POST /transfers

**Request:**
```json
{
  "events": [
    {
      "event_id": "evt-001",
      "station_id": "S1",
      "amount": 100.50,
      "status": "approved",
      "created_at": "2026-02-19T10:00:00Z"
    }
  ]
}
```

**Response (201):**
```json
{ "inserted": 7, "duplicates": 3 }
```

**Validation (fail-fast):** The entire batch is validated before any DB write. If any event is invalid → `400` with a descriptive error. Required fields: `event_id`, `station_id`, `status`, `created_at`. `amount` must be `>= 0`.

### GET /stations/{station_id}/summary

**Response (200):**
```json
{
  "station_id": "S1",
  "total_approved_amount": 450.25,
  "events_count": 12
}
```

- `events_count` = total stored events for the station (all statuses)
- `total_approved_amount` = sum of `amount` where `status = 'approved'`
- `404` if no events found for that `station_id`

---

## Decisions Documented

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Error strategy | Fail-fast | Simpler, atomic, easier to reason about |
| events_count | All statuses | More informative, matches assignment default |
| Concurrency | DB unique constraint | Atomic, no extra deps, idiomatic Postgres |
| Storage | PostgreSQL via Docker | Real constraints, deterministic queries |

---

## Testing Plan

6 tests using `pytest` + `httpx` async client against a real test Postgres DB:

1. Batch insert → correct `inserted`/`duplicates`
2. Re-send same batch → all duplicates, totals unchanged
3. Out-of-order `created_at` → same summary totals
4. Concurrent POSTs with same `event_id` → single insert (no double-count)
5. Summary endpoint returns correct `total_approved_amount` per station
6. Invalid payload → 400 with descriptive error message