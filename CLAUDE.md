# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (including test extras)
pip install -e ".[test]"

# Start Postgres (required for running app and tests)
docker compose up db -d

# Run the app
make run                        # uvicorn app.main:app --reload

# Run tests
make test                       # pytest tests/ -v
pytest tests/test_transfers.py  # single test file
pytest tests/ -v -k "test_name" # single test by name

# Run everything in Docker
make docker-up                  # build + run app + db
make docker-test                # run tests inside Docker
```

## Architecture

Layered FastAPI service with a single domain: `transfer_events`.

```
app/
├── main.py          # FastAPI app, lifespan (table creation), 400 exception handler
├── db.py            # Async SQLAlchemy engine + session factory; reads DATABASE_URL
├── api/routes.py    # Two endpoints: POST /transfers, GET /stations/{id}/summary
├── services/        # Business logic; calls store interface
├── store/
│   ├── base.py      # AbstractTransferStore interface
│   └── postgres.py  # PostgresTransferStore; bulk insert with ON CONFLICT DO NOTHING
├── models/          # SQLAlchemy ORM (transfer_events table)
└── schemas/         # Pydantic request/response validation
```

**Data flow:** `routes.py` → `TransferService` → `AbstractTransferStore` (injected via FastAPI DI).

**Key design decisions:**
- Idempotency is enforced at the DB level via `event_id PRIMARY KEY` + `ON CONFLICT (event_id) DO NOTHING`. No application-level deduplication.
- Fail-fast validation: Pydantic validates the entire batch before any DB write; any invalid event returns `400`, no partial inserts.
- `events_count` in summaries counts all statuses; `total_approved_amount` filters to `status = 'approved'`.
- The store abstraction (`AbstractTransferStore`) exists to allow swapping persistence (e.g., in-memory) by overriding the `get_session` FastAPI dependency.

**Test infrastructure** (`tests/conftest.py`): creates a separate `petro_test` DB, overrides the `get_session` dependency with a test session, and truncates tables between tests. `pytest-asyncio` is configured with `asyncio_mode = "auto"` (session-scoped loop).
