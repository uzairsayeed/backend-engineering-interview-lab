# Implementation Stages

This document tracks the planned implementation of the Multi-Tenant Cloud
Resource Quota Manager. A stage is complete only when its evaluation checks
pass. Each stage requires approval before implementation begins.

## Stage 1: Runnable project skeleton

Status: Complete

### What we are doing

- Declare the Python 3.11 project and its runtime and test dependencies.
- Create the application package.
- Read the database URL from configuration, with a persistent SQLite default.
- Create the SQLAlchemy engine and one-session-per-request dependency.
- Create a minimal FastAPI application.
- Add a health endpoint for a simple runtime check.

### Files

- Create `pyproject.toml`: declare Python compatibility, dependencies, and
  Pytest configuration.
- Create `app/__init__.py`: mark `app` as the application package.
- Create `app/config.py`: provide the configurable, file-backed database URL.
- Create `app/database.py`: provide the engine, session factory, declarative
  base, and request-scoped session dependency.
- Create `app/main.py`: create the FastAPI application and health endpoint.
- Create `IMPLEMENTATION_STAGES.md`: track scope and completion criteria.

### Dependencies

- `app/database.py` depends on `app/config.py`.
- Future persistence models depend on the base in `app/database.py`.
- Future HTTP routes will be registered by `app/main.py`.
- `pyproject.toml` supplies the application's external packages.

### How to evaluate it

1. Install the project dependencies.
2. Start the application with `uvicorn app.main:app`.
3. Confirm startup completes without import or configuration errors.
4. Open `/docs` and confirm FastAPI's OpenAPI page loads.
5. Call `GET /health` and confirm it returns `200` with `{"status": "ok"}`.
6. Confirm the default database URL points to a file, not in-memory SQLite.

### Evaluation commands

```bash
source .venv/bin/activate
uvicorn app.main:app
```

In another terminal:

```bash
curl -i http://127.0.0.1:8000/health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/docs
python -c "from app.database import engine; print(engine.url)"
```

## Stage 2: Domain and persistence model

Status: Complete

### What we are doing

- Define reservation states and domain errors.
- Model tenant quotas and reservations with SQLAlchemy.
- Add database constraints that prevent negative resource values.
- Configure Alembic and create the initial schema migration.
- Seed five tenants with identical quotas and zero usage.

### Files

- Create `app/domain.py`: define reservation statuses and domain errors.
- Create `app/models.py`: define tenant quota and reservation SQLAlchemy
  models, constraints, relationships, and indexes.
- Create `alembic.ini`: provide Alembic command-line configuration.
- Create `alembic/env.py`: connect Alembic to application configuration and
  model metadata.
- Create `alembic/script.py.mako`: provide the standard migration template.
- Create `alembic/versions/0001_create_quota_tables.py`: create and remove the
  initial database schema and seed `tenant-1` through `tenant-5` with 4000 CPU
  millicores, 8192 MiB memory, 2 GPUs, and zero usage.
- Modify `IMPLEMENTATION_STAGES.md`: update the stage status.

### Dependencies

- `app/models.py` depends on `app/database.py` and `app/domain.py`.
- `alembic/env.py` depends on `app/config.py`, `app/database.py`, and
  `app/models.py`.
- The initial migration reflects the schema defined by `app/models.py`.
- `alembic.ini` points Alembic commands to `alembic/env.py`.

### How to evaluate it

1. Run `alembic upgrade head` against a new SQLite database.
2. Confirm the quota and reservation tables are created.
3. Confirm the expected constraints and indexes are present.
4. Confirm exactly five seeded tenants have the documented quota and zero
   usage.
5. Run `alembic downgrade base` and `alembic upgrade head` successfully.
6. Confirm the seed data is recreated once without duplicate tenants.
7. Restart the application and confirm the file-backed database remains.

### Evaluation commands

Use a disposable database so downgrade testing cannot remove development data:

```bash
export DATABASE_URL=sqlite:////tmp/quota_manager_stage2.db
rm -f /tmp/quota_manager_stage2.db
alembic upgrade head
alembic current
sqlite3 /tmp/quota_manager_stage2.db ".tables"
sqlite3 -header -column /tmp/quota_manager_stage2.db \
  "SELECT * FROM tenant_quotas ORDER BY tenant_id;"
sqlite3 /tmp/quota_manager_stage2.db ".schema tenant_quotas"
sqlite3 /tmp/quota_manager_stage2.db ".schema reservations"
alembic check
alembic downgrade base
alembic upgrade head
sqlite3 /tmp/quota_manager_stage2.db \
  "SELECT COUNT(*) FROM tenant_quotas;"
unset DATABASE_URL
```

The final count must be `5`.

## Stage 3: Quota vertical slice

Status: Complete

### What we are doing

- Define quota request and response schemas.
- Add quota repository operations without repository-owned commits.
- Implement quota replacement and retrieval in the service layer.
- Reject quota updates below current usage.
- Expose quota endpoints and consistent API error responses.
- Verify database connectivity during application startup and dispose the
  connection pool during shutdown.
- Translate unexpected SQLAlchemy failures into a safe, consistent `500`
  response while retaining details in application logs.

### Files

- Create `app/schemas.py`: define validated HTTP request, response, and error
  contracts.
- Create `app/repositories.py`: implement quota persistence operations without
  committing transactions.
- Create `app/services.py`: implement quota business rules and mutation
  transaction boundaries.
- Create `app/routes.py`: expose quota endpoints and map service results to
  HTTP responses.
- Modify `app/main.py`: register routes, application lifespan behavior, and
  consistent domain, validation, HTTP, and database exception handlers.
- Modify `IMPLEMENTATION_STAGES.md`: update the stage status.

### Dependencies

- `app/schemas.py` depends on the status vocabulary in `app/domain.py`.
- `app/repositories.py` depends on `app/models.py`.
- `app/services.py` depends on `app/domain.py` and `app/repositories.py`.
- `app/routes.py` depends on `app/database.py`, `app/schemas.py`, and
  `app/services.py`.
- `app/main.py` depends on `app/database.py`, `app/routes.py`, domain error
  definitions, and SQLAlchemy's base exception type.

### How to evaluate it

1. Configure a tenant quota with `PUT /tenants/{tenant_id}/quota`.
2. Retrieve it with `GET /tenants/{tenant_id}/quota`.
3. Confirm initial usage is zero.
4. Confirm replacing the quota returns the new limits.
5. Confirm negative values return a consistent validation error.
6. Confirm an unknown tenant returns a meaningful `404`.
7. Restart the application and confirm the quota remains available.
8. Confirm startup logs application metadata and verifies the database.
9. Confirm shutdown disposes the engine and logs application termination.
10. Confirm a SQLAlchemy request failure returns a safe `500` error without
    exposing database details.

### Evaluation commands

With the application running:

```bash
curl -i -X PUT http://127.0.0.1:8000/tenants/tenant-stage3/quota \
  -H "Content-Type: application/json" \
  -d '{"cpu":4000,"memory":8192,"gpu":2}'

curl -i http://127.0.0.1:8000/tenants/tenant-stage3/quota

curl -i -X PUT http://127.0.0.1:8000/tenants/tenant-stage3/quota \
  -H "Content-Type: application/json" \
  -d '{"cpu":8000,"memory":16384,"gpu":4}'

curl -i -X PUT http://127.0.0.1:8000/tenants/invalid/quota \
  -H "Content-Type: application/json" \
  -d '{"cpu":-1,"memory":1024,"gpu":0}'

curl -i http://127.0.0.1:8000/tenants/unknown-tenant/quota
```

Restart Uvicorn and repeat the quota `GET` to verify persistence.

## Stage 4: Reservation vertical slice

Status: Complete

### What we are doing

- Create all-or-nothing reservations.
- Retrieve and list tenant-scoped reservations.
- Release reservations while decrementing usage exactly once.
- Atomically enforce all CPU, memory, and GPU limits.
- Preserve tenant isolation and return meaningful errors.

### Files

- Modify `app/schemas.py`: add reservation request and response contracts.
- Modify `app/repositories.py`: add atomic reservation, lookup, listing, and
  release persistence operations.
- Modify `app/services.py`: add reservation allocation and release rules with
  service-owned transactions.
- Modify `app/routes.py`: add create, retrieve, list, and release endpoints.
- Modify `IMPLEMENTATION_STAGES.md`: update the stage status.

### Dependencies

- Reservation schemas use statuses from `app/domain.py`.
- Reservation repository operations use both models from `app/models.py`.
- Reservation services coordinate repository operations in one transaction.
- Reservation routes use the request session from `app/database.py` and call
  `app/services.py`.

### How to evaluate it

1. Create a reservation within quota and receive `201`.
2. Confirm all three usage values increase in the same operation.
3. Retrieve the reservation and list it under its tenant.
4. Reject a reservation when any resource would exceed quota.
5. Confirm a rejected request changes no usage and creates no reservation.
6. Release an active reservation and confirm usage decreases.
7. Release it again and confirm usage does not decrease again.
8. Confirm one tenant's reservations do not affect another tenant.

### Evaluation commands

Configure a tenant, then create a reservation:

```bash
curl -i -X PUT http://127.0.0.1:8000/tenants/tenant-stage4/quota \
  -H "Content-Type: application/json" \
  -d '{"cpu":4000,"memory":8192,"gpu":2}'

curl -i -X POST \
  http://127.0.0.1:8000/tenants/tenant-stage4/reservations \
  -H "Content-Type: application/json" \
  -d '{"cpu":1000,"memory":2048,"gpu":1}'

curl -i http://127.0.0.1:8000/tenants/tenant-stage4/quota
curl -i http://127.0.0.1:8000/tenants/tenant-stage4/reservations
```

Copy the returned reservation ID into `RESERVATION_ID`, then run:

```bash
export RESERVATION_ID="<returned-id>"
curl -i \
  "http://127.0.0.1:8000/tenants/tenant-stage4/reservations/$RESERVATION_ID"
curl -i -X POST \
  "http://127.0.0.1:8000/tenants/tenant-stage4/reservations/$RESERVATION_ID/release"
curl -i -X POST \
  "http://127.0.0.1:8000/tenants/tenant-stage4/reservations/$RESERVATION_ID/release"
curl -i http://127.0.0.1:8000/tenants/tenant-stage4/quota
```

Confirm all-or-nothing rejection:

```bash
curl -i -X POST \
  http://127.0.0.1:8000/tenants/tenant-stage4/reservations \
  -H "Content-Type: application/json" \
  -d '{"cpu":4001,"memory":1,"gpu":0}'
```

The final request must return `409`, create no reservation, and leave usage
unchanged.

## Stage 5: Automated correctness tests

Status: Complete

### What we are doing

- Run API tests against an isolated file-backed SQLite database.
- Cover quota and reservation behavior, validation, and tenant isolation.
- Exercise concurrent reservation and release attempts with independent
  sessions.

### Files

- Create `tests/conftest.py`: provide a temporary file-backed database,
  application dependency override, and test client.
- Create `tests/test_api.py`: cover quota and reservation HTTP behavior and
  invariants.
- Create `tests/test_concurrency.py`: exercise competing allocations and
  releases with independent sessions.
- Modify `IMPLEMENTATION_STAGES.md`: update the stage status.

### Dependencies

- `tests/conftest.py` depends on `app/database.py` and `app/main.py`.
- `tests/test_api.py` depends on fixtures from `tests/conftest.py` and the
  completed HTTP API.
- `tests/test_concurrency.py` depends on `app/models.py`, `app/services.py`,
  and isolated session factories.

### How to evaluate it

1. Run `pytest`.
2. Confirm all tests pass from a clean checkout and database.
3. Confirm concurrent requests cannot make usage exceed quota.
4. Confirm concurrent releases decrement usage only once.
5. Confirm usage is never negative.

### Evaluation commands

```bash
source .venv/bin/activate
pytest
pytest tests/test_api.py
pytest tests/test_concurrency.py
```

All commands must exit successfully. The full suite must pass when run more
than once.

## Stage 6: Documentation and final verification

Status: Complete

### What we are doing

- Document setup, migration, server, test, and API usage.
- Record assumptions, invariants, transaction design, and trade-offs.
- Perform a clean end-to-end verification.

### Files

- Create `README.md`: document setup, migration, run, test, units, and API
  usage.
- Create `DESIGN.md`: document assumptions, layers, invariants, transaction
  strategy, concurrency behavior, and deliberate exclusions.
- Modify `IMPLEMENTATION_STAGES.md`: mark final verification complete.

### Dependencies

- `README.md` depends on the final commands, endpoints, and project layout.
- `DESIGN.md` depends on the final models, service rules, and concurrency
  implementation.
- Final verification depends on all prior stages.

### How to evaluate it

1. Follow only the README instructions from a clean environment.
2. Apply migrations to a new database.
3. Run the full test suite.
4. Start the API and complete one quota-reservation-release workflow.
5. Confirm repositories never commit transactions.
6. Confirm the design document explains SQLite's concurrency limitations.

### Evaluation commands

```bash
source .venv/bin/activate
export DATABASE_URL=sqlite:////tmp/quota_manager_final.db
rm -f /tmp/quota_manager_final.db
alembic upgrade head
pytest
uvicorn app.main:app
```

In another terminal, run the Stage 1 health check and the Stage 4 API workflow.
Then inspect repository transaction ownership:

```bash
rg "\.commit\(" app/repositories.py
```

The search must return no repository commits. Finally, follow `README.md`
without relying on undocumented setup steps and review `DESIGN.md` against the
implemented behavior.
