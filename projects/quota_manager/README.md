# Multi-Tenant Cloud Resource Quota Manager

A small FastAPI service that configures tenant quotas and atomically allocates
CPU, memory, and GPU reservations. Data is persisted in a file-backed SQLite
database.

## Resource units

- CPU: millicores
- Memory: MiB
- GPU: whole GPU count

All quantities are non-negative integers.

## Requirements

- Python 3.11
- `uv`, or another Python environment and package installer

## Setup

Create and activate a Python 3.11 virtual environment:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Apply the database migration:

```bash
alembic upgrade head
```

The migration creates `quota_manager.db` by default and seeds `tenant-1`
through `tenant-5`. Each seeded tenant has:

- 4000 CPU millicores
- 8192 MiB memory
- 2 GPUs
- Zero initial usage

## Run

```bash
source .venv/bin/activate
uvicorn app.main:app
```

The API is available at `http://127.0.0.1:8000`. OpenAPI documentation is
available at `http://127.0.0.1:8000/docs`.

Check process health:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Configuration

Set `DATABASE_URL` to use a different SQLite file:

```bash
export DATABASE_URL=sqlite:///./another.db
alembic upgrade head
uvicorn app.main:app
```

The same value must be present when running migrations and the application.

## API

### Configure or replace quota

```bash
curl -X PUT http://127.0.0.1:8000/tenants/tenant-a/quota \
  -H "Content-Type: application/json" \
  -d '{"cpu":4000,"memory":8192,"gpu":2}'
```

This operation also establishes a previously unknown tenant. Replacing a quota
below current usage returns `409 Conflict` without changing the quota.

### Retrieve quota and usage

```bash
curl http://127.0.0.1:8000/tenants/tenant-a/quota
```

### Create reservation

```bash
curl -X POST http://127.0.0.1:8000/tenants/tenant-a/reservations \
  -H "Content-Type: application/json" \
  -d '{"cpu":1000,"memory":2048,"gpu":1}'
```

The response contains the server-generated reservation ID. If any requested
resource exceeds available quota, the entire request returns `409 Conflict`
and no usage is allocated.

### Retrieve reservation

```bash
curl \
  http://127.0.0.1:8000/tenants/tenant-a/reservations/RESERVATION_ID
```

### List tenant reservations

```bash
curl http://127.0.0.1:8000/tenants/tenant-a/reservations
```

The response includes active and released reservations ordered by creation
time.

### Release reservation

```bash
curl -X POST \
  http://127.0.0.1:8000/tenants/tenant-a/reservations/RESERVATION_ID/release
```

Release is idempotent. Releasing an already released reservation returns its
current state and does not decrement usage again.

## Error format

API errors use a consistent envelope:

```json
{
  "error": {
    "code": "QUOTA_EXCEEDED",
    "message": "Insufficient quota for the requested resources",
    "details": {
      "resources": ["cpu"]
    }
  }
}
```

Common status codes:

- `200`: successful quota operation, retrieval, listing, or release
- `201`: reservation created
- `404`: quota or tenant-scoped reservation not found
- `409`: quota below usage or insufficient available quota
- `422`: invalid request
- `500`: unexpected database failure

## Tests

Tests use fresh temporary file-backed SQLite databases and do not modify the
development database.

```bash
source .venv/bin/activate
pytest
```

Run individual suites:

```bash
pytest tests/test_api.py
pytest tests/test_concurrency.py
```

## Migration commands

```bash
alembic current
alembic upgrade head
alembic downgrade base
```

Only use downgrade against a disposable database because it removes quota and
reservation data.

See `DESIGN.md` for architectural decisions, invariants, and concurrency
trade-offs.
