# Background Job Service — Incremental Implementation Stages

This document is the implementation checklist for the interview. Complete and
verify one stage before starting the next. At the start of every stage, restate
the files listed under **Files created or modified** and do not touch unrelated
files.

## Working rules

- Keep the implementation limited to the confirmed requirements and assumptions.
- Repositories may call `flush()`, but never own the outer transaction commit.
- Use one SQLAlchemy session per HTTP request.
- Worker units of work use their own short-lived sessions.
- Commit a newly created or retried job before placing its ID on the in-process queue.
- Use explicit state-conditional SQL updates for worker claims, cancellation,
  completion, and retry.
- Do not hold a database session or transaction open while a job sleeps.
- Do not add optional infrastructure or abstractions.
- Do not begin a later stage until the current stage's checks pass.

---

## Stage 1 — Project skeleton and domain vocabulary [COMPLETED]

### What we are implementing

- Python 3.11 project metadata and required dependencies.
- The application package.
- The job lifecycle enum and focused domain exceptions.
- No database, HTTP API, or worker behavior yet.

### Files created or modified

1. `pyproject.toml` — create
2. `app/__init__.py` — create
3. `app/domain.py` — create

### File responsibilities and dependencies

- `pyproject.toml`
  - Declares Python 3.11.
  - Declares FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic, Pydantic, Pytest, and
    HTTPX.
  - Configures Pytest test discovery.
- `app/__init__.py`
  - Marks `app` as a package and contains no behavior.
- `app/domain.py`
  - Defines `JobStatus`: `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, and
    `CANCELLED`.
  - Defines focused exceptions for job-not-found, invalid cancellation,
    invalid retry, and retry-limit exhaustion.
  - Has no dependency on FastAPI, SQLAlchemy, or the worker.

Dependency direction:

```text
pyproject.toml
└── app package
    └── domain.py
```

### Expected result

- Dependencies install successfully under Python 3.11.
- The application package imports.
- Every required state is represented exactly once.
- Domain code has no framework dependencies.

### Commands to verify the stage

1. Confirm Python:

   ```bash
   python3.11 --version
   ```

2. Create and activate a virtual environment:

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the project and test dependencies:

   ```bash
   python -m pip install -e ".[test]"
   ```

4. Compile and import the package:

   ```bash
   python -m compileall -q app
   python -c "from app.domain import JobStatus; assert [s.value for s in JobStatus] == ['PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED']"
   ```

Stage 1 passes when every command exits with status `0`.

---

## Stage 2 — SQLite persistence and Alembic migration [COMPLETED]

### What we are implementing

- SQLAlchemy engine, declarative base, and session factory.
- The single `jobs` ORM model.
- The initial Alembic migration.
- Database-level constraints and the one justified index.
- No repository or lifecycle operations yet.

### Files created or modified

1. `app/database.py` — create
2. `app/models.py` — create
3. `alembic.ini` — create
4. `alembic/env.py` — create
5. `alembic/versions/0001_create_jobs.py` — create

No Stage 1 file should be modified unless a verified import issue requires it.

### File responsibilities and dependencies

- `app/database.py`
  - Defines the SQLAlchemy `Base`, persistent SQLite engine, and `SessionLocal`.
  - Reads an optional `DATABASE_URL`, defaulting to a local persistent SQLite file.
  - Uses SQLite's `check_same_thread=False`.
  - Will later provide the request session dependency.
- `app/models.py`
  - Defines only the `jobs` table.
  - Depends on `Base` from `app/database.py` and `JobStatus` from
    `app/domain.py`.
  - Stores UUID string ID, duration, failure flag, state, retry count, failure
    reason, and UTC lifecycle timestamps.
  - Adds checks for duration `1..10`, valid status values, and retry count
    `0..3`.
  - Adds one non-unique index on `status`.
  - Adds no foreign keys and no additional unique constraints.
- `alembic.ini`
  - Configures the Alembic script location.
- `alembic/env.py`
  - Depends on `app/database.py` and imports `app/models.py`.
  - Exposes `Base.metadata` to Alembic.
- `alembic/versions/0001_create_jobs.py`
  - Reproduces the model's table, checks, and index in `upgrade()`.
  - Fully removes them in `downgrade()`.

Dependency direction:

```text
domain.py ───────────────┐
                        v
database.py ────────> models.py
     │                   │
     └──────> alembic/env.py
                         │
                         v
             0001_create_jobs.py
```

### Expected result

- `alembic upgrade head` creates a persistent SQLite database.
- The database contains exactly the `jobs` table plus Alembic's version table.
- The `jobs` table has the expected primary key, checks, and `status` index.
- Upgrade and downgrade both work.

### Commands to verify the stage

Run all commands with the Stage 1 virtual environment active.

1. Apply the migration to a disposable stage database:

   ```bash
   DATABASE_URL=sqlite:///./stage.db alembic upgrade head
   ```

2. Inspect tables, columns, checks, and indexes through SQLAlchemy:

   ```bash
   DATABASE_URL=sqlite:///./stage.db python - <<'PY'
   from sqlalchemy import create_engine, inspect

   inspector = inspect(create_engine("sqlite:///./stage.db"))
   assert set(inspector.get_table_names()) == {"alembic_version", "jobs"}
   assert {column["name"] for column in inspector.get_columns("jobs")} == {
       "id",
       "duration_seconds",
       "should_fail",
       "status",
       "retry_count",
       "failure_reason",
       "created_at",
       "updated_at",
       "started_at",
       "completed_at",
   }
   assert any(index["column_names"] == ["status"] for index in inspector.get_indexes("jobs"))
   assert len(inspector.get_check_constraints("jobs")) >= 3
   PY
   ```

3. Verify downgrade and re-upgrade:

   ```bash
   DATABASE_URL=sqlite:///./stage.db alembic downgrade base
   DATABASE_URL=sqlite:///./stage.db alembic upgrade head
   ```

Stage 2 passes when the migration round-trip and schema assertions succeed.

---

## Stage 3 — API schemas, repository, and lifecycle service [COMPLETED]

### What we are implementing

- Pydantic request and response contracts.
- Persistence operations for creating, reading, scanning, and transitioning jobs.
- Service-level lifecycle rules and domain errors.
- Atomic state transitions, without HTTP or queue integration.

### Files created or modified

1. `app/schemas.py` — create
2. `app/repository.py` — create
3. `app/service.py` — create

No Stage 1 or Stage 2 file should be modified unless an implementation defect is
found while verifying this stage.

### File responsibilities and dependencies

- `app/schemas.py`
  - Depends on `app/domain.py`.
  - Defines `JobCreate` with inclusive validation for `duration_seconds`.
  - Defines `JobResponse` and a stable error envelope.
  - Contains no database or HTTP routing behavior.
- `app/repository.py`
  - Depends on `app/models.py` and `app/domain.py`.
  - Creates and retrieves jobs and lists persisted `PENDING` IDs.
  - Performs explicit conditional updates:
    - claim: `PENDING → RUNNING`
    - cancel: `PENDING → CANCELLED`
    - complete: `RUNNING → SUCCEEDED|FAILED`
    - retry: `FAILED → PENDING` where `retry_count < 3`
  - Checks affected-row count.
  - May flush but never commits.
- `app/service.py`
  - Depends on `app/repository.py`, `app/models.py`, and `app/domain.py`.
  - Implements create, get, cancel, retry, claim, and completion use cases.
  - On a failed conditional update, rereads state and raises the precise domain
    error.
  - Retry preserves ID, increments `retry_count`, and clears previous failure
    and execution fields.
  - Has no FastAPI or queue dependency.

Dependency direction:

```text
domain.py ─────> schemas.py
    │
    └────> models.py ─────> repository.py ─────> service.py
```

### Expected result

- Invalid creation payloads are rejected by Pydantic.
- A created job begins as `PENDING` with `retry_count == 0`.
- Cancel, claim, complete, and retry follow only the allowed transitions.
- Invalid operations raise domain errors.
- Repository methods do not commit; the caller controls transaction outcome.
- Two competing `PENDING` transitions cannot both report success.

### Commands to verify the stage

1. Compile the application:

   ```bash
   python -m compileall -q app
   ```

2. Confirm Pydantic boundaries:

   ```bash
   python - <<'PY'
   from pydantic import ValidationError
   from app.schemas import JobCreate

   assert JobCreate(duration_seconds=1, should_fail=False).duration_seconds == 1
   assert JobCreate(duration_seconds=10, should_fail=True).duration_seconds == 10

   for invalid in (0, 11):
       try:
           JobCreate(duration_seconds=invalid, should_fail=False)
       except ValidationError:
           pass
       else:
           raise AssertionError(f"{invalid} should be rejected")
   PY
   ```

3. Run a focused service smoke script against the migrated stage database:

   ```bash
   DATABASE_URL=sqlite:///./stage.db python - <<'PY'
   from app.database import SessionLocal
   from app.schemas import JobCreate
   from app.service import JobService
   from app.domain import JobStatus

   with SessionLocal() as session:
       service = JobService(session)
       job = service.create(JobCreate(duration_seconds=1, should_fail=False))
       job_id = job.id
       assert job.status == JobStatus.PENDING
       assert job.retry_count == 0
       session.commit()

   with SessionLocal() as session:
       service = JobService(session)
       cancelled = service.cancel(job_id)
       assert cancelled.status == JobStatus.CANCELLED
       session.commit()
   PY
   ```

Stage 3 passes when validation, persistence, and one allowed transition work and
the service never commits internally.

---

## Stage 4 — In-process FIFO worker

### What we are implementing

- One application-local FIFO queue.
- One consumer task.
- Atomic job claiming and deterministic execution.
- Separate short database transactions before and after the sleep.
- Safe handling of stale or duplicate queued IDs.

### Files created or modified

1. `app/worker.py` — create

Existing files should only be modified if verification exposes a missing
service/repository operation required by the worker.

### File responsibilities and dependencies

- `app/worker.py`
  - Depends on `app/database.py`, `app/service.py`, and `app/domain.py`.
  - Owns `asyncio.Queue`, worker task start/stop, and enqueue operations.
  - Opens a short-lived session to conditionally claim and commit.
  - Closes that session before `asyncio.sleep(duration_seconds)`.
  - Opens a new short-lived session to conditionally complete and commit.
  - Uses `should_fail` to select `SUCCEEDED` or `FAILED`.
  - Stores the stable failure reason `Job configured to fail`.
  - Does not retry failed jobs automatically.

Dependency direction:

```text
database.py ─┐
service.py ──┼──> worker.py
domain.py ───┘
```

### Expected result

- Enqueue returns without waiting for the configured duration.
- A successful job eventually reaches `SUCCEEDED`.
- A configured failure eventually reaches `FAILED` with a failure reason.
- Duplicate queue entries do not execute the same attempt twice.
- The worker shuts down without leaking its consumer task.

### Commands to verify the stage

1. Compile the application:

   ```bash
   python -m compileall -q app
   ```

2. Run a successful worker smoke check:

   ```bash
   DATABASE_URL=sqlite:///./stage.db python - <<'PY'
   import asyncio

   from app.database import SessionLocal
   from app.domain import JobStatus
   from app.schemas import JobCreate
   from app.service import JobService
   from app.worker import BackgroundWorker

   async def main():
       with SessionLocal() as session:
           job = JobService(session).create(
               JobCreate(duration_seconds=1, should_fail=False)
           )
           job_id = job.id
           session.commit()

       worker = BackgroundWorker(SessionLocal)
       await worker.start()
       await worker.enqueue(job_id)
       await asyncio.sleep(1.5)

       with SessionLocal() as session:
           job = JobService(session).get(job_id)
           assert job.status == JobStatus.SUCCEEDED

       await worker.stop()

   asyncio.run(main())
   PY
   ```

Stage 4 passes when the job reaches `SUCCEEDED` and the process exits cleanly.

---

## Stage 5 — HTTP API and runnable application checkpoint

### What we are implementing

- Four required HTTP endpoints.
- One request-scoped SQLAlchemy session.
- 404, 409, and 422 behavior.
- Commit-before-enqueue ordering.
- FastAPI lifespan ownership of the worker.
- Startup scheduling of persisted `PENDING` jobs.
- This is the first complete runnable vertical slice.

### Files created or modified

1. `app/api.py` — create
2. `app/main.py` — create
3. `app/database.py` — modify only to expose the request session dependency if
   it was not completed in Stage 2

### File responsibilities and dependencies

- `app/api.py`
  - Depends on `app/schemas.py`, `app/service.py`, `app/database.py`, and the
    worker stored in application state.
  - Defines:
    - `POST /jobs` → `202 Accepted`
    - `GET /jobs/{job_id}` → `200 OK`
    - `POST /jobs/{job_id}/cancel` → `200 OK`
    - `POST /jobs/{job_id}/retry` → `202 Accepted`
  - Maps unknown IDs to `404`.
  - Maps invalid lifecycle operations and exhausted retries to `409`.
  - Leaves malformed payloads as FastAPI/Pydantic `422`.
  - Commits create/retry before enqueueing the job ID.
- `app/main.py`
  - Depends on `app/api.py`, `app/worker.py`, `app/database.py`, and
    `app/service.py`.
  - Creates the FastAPI application and lifespan.
  - Starts one worker, scans and enqueues persisted `PENDING` IDs, and stops the
    worker on shutdown.
  - Does not recover interrupted `RUNNING` jobs.
- `app/database.py`
  - Supplies exactly one session per request and closes it reliably.

Dependency direction:

```text
schemas.py ───┐
service.py ───┼──> api.py ───────┐
database.py ──┘                   │
                                 v
database.py ──> worker.py ───> main.py
```

### Expected result

- The server starts after `alembic upgrade head`.
- Creation responds before execution completes.
- Status polling observes the correct terminal state.
- Cancelling only succeeds while `PENDING`.
- Retrying only succeeds while `FAILED` and under the retry limit.
- IDs remain unchanged across retries.
- Restarting the application schedules persisted `PENDING` jobs.
- No endpoint commits from inside a repository.

### Commands to verify the stage

Use two terminals with the virtual environment active.

#### Terminal 1 — migrate and start the API

1. Apply migrations:

   ```bash
   DATABASE_URL=sqlite:///./stage-api.db alembic upgrade head
   ```

2. Start the server:

   ```bash
   DATABASE_URL=sqlite:///./stage-api.db uvicorn app.main:app --reload
   ```

#### Terminal 2 — exercise the vertical slice

3. Create a successful job and capture its ID:

   ```bash
   JOB_ID=$(curl -s -X POST http://127.0.0.1:8000/jobs \
     -H 'Content-Type: application/json' \
     -d '{"duration_seconds":1,"should_fail":false}' \
     | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')
   echo "$JOB_ID"
   ```

4. Retrieve it immediately, then after execution:

   ```bash
   curl -s "http://127.0.0.1:8000/jobs/$JOB_ID"
   sleep 2
   curl -s "http://127.0.0.1:8000/jobs/$JOB_ID"
   ```

   The final state must be `SUCCEEDED`.

5. Create a failing job:

   ```bash
   FAILED_ID=$(curl -s -X POST http://127.0.0.1:8000/jobs \
     -H 'Content-Type: application/json' \
     -d '{"duration_seconds":1,"should_fail":true}' \
     | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')
   sleep 2
   curl -s "http://127.0.0.1:8000/jobs/$FAILED_ID"
   ```

   The state must be `FAILED` and `failure_reason` must be populated.

6. Retry the failed job:

   ```bash
   curl -i -X POST "http://127.0.0.1:8000/jobs/$FAILED_ID/retry"
   ```

   The response must be `202`, retain the same ID, show `PENDING`, and set
   `retry_count` to `1`.

7. Verify `404`:

   ```bash
   curl -i "http://127.0.0.1:8000/jobs/00000000-0000-0000-0000-000000000000"
   ```

8. Verify `422`:

   ```bash
   curl -i -X POST http://127.0.0.1:8000/jobs \
     -H 'Content-Type: application/json' \
     -d '{"duration_seconds":11,"should_fail":false}'
   ```

Stage 5 passes when the API is runnable and all commands return the expected
state and status codes.

---

## Stage 6 — Three focused integration tests

### What we are implementing

- Isolated SQLite integration-test setup.
- Bounded asynchronous polling.
- Exactly three end-to-end tests covering the highest-risk behavior.

### Files created or modified

1. `tests/conftest.py` — create
2. `tests/test_jobs.py` — create

Production files should only be modified when a test exposes a confirmed defect.

### File responsibilities and dependencies

- `tests/conftest.py`
  - Depends on `app/main.py`, `app/database.py`, and `app/models.py`.
  - Creates an isolated temporary SQLite database.
  - Overrides the request session dependency and worker session factory.
  - Owns TestClient/lifespan cleanup.
  - Provides polling with a strict deadline rather than unbounded sleeps.
- `tests/test_jobs.py`
  - Depends on fixtures from `tests/conftest.py`.
  - Contains exactly three tests:
    1. Create returns `202` promptly and eventually becomes `SUCCEEDED`.
    2. Intentional failure records a reason; retry retains ID and increments
       count; an exhausted retry returns `409`.
    3. Keep the sole worker busy, cancel a second `PENDING` job, and verify that
       it remains `CANCELLED`.

Dependency direction:

```text
app/main.py + app/database.py + app/models.py
                    │
                    v
             tests/conftest.py
                    │
                    v
             tests/test_jobs.py
```

### Expected result

- Test data never touches the development database.
- Tests start and stop the real in-process worker.
- Polling fails with a useful timeout instead of hanging.
- All three tests pass repeatedly.
- Test collection reports exactly three tests.

### Commands to verify the stage

1. List collected tests:

   ```bash
   pytest --collect-only -q
   ```

   Confirm exactly three tests are collected.

2. Run the integration suite:

   ```bash
   pytest -q
   ```

3. Repeat once to detect leaked state or lifecycle tasks:

   ```bash
   pytest -q
   ```

Stage 6 passes when both runs report three passing tests.

---

## Stage 7 — Required documentation and final verification

### What we are implementing

- Run instructions and API examples.
- Lifecycle and transaction explanation.
- Explicit assumptions and scope exclusions.
- The required limitation for interrupted `RUNNING` jobs.
- Final clean-room verification.

### Files created or modified

1. `README.md` — create

No production or test file should be modified unless final verification finds a
confirmed defect.

### File responsibilities and dependencies

- `README.md`
  - Depends on the final behavior of every earlier stage.
  - Documents installation, migration, server, and test commands.
  - Documents request/response behavior and lifecycle transitions.
  - Explains atomic state-conditional updates and commit-before-enqueue.
  - States that the design supports one process and one FIFO worker.
  - Explicitly states that interrupted `RUNNING` jobs are not recovered and may
    remain stranded.
  - Lists excluded production concerns without proposing implementations.

Dependency direction:

```text
Stages 1–6 ─────> README.md
```

### Expected result

- A reviewer can install, migrate, run, and test the application using only the
  README.
- The documented API matches the implemented API.
- The limitation around interrupted `RUNNING` jobs is prominent.
- Migration and tests succeed from a clean disposable database.

### Commands to verify the stage

1. Compile the application:

   ```bash
   python -m compileall -q app tests
   ```

2. Apply the migration to a fresh smoke database:

   ```bash
   DATABASE_URL=sqlite:///./final-smoke.db alembic upgrade head
   ```

3. Run all tests:

   ```bash
   pytest -q
   ```

4. Start the final smoke server:

   ```bash
   DATABASE_URL=sqlite:///./final-smoke.db uvicorn app.main:app
   ```

5. In another terminal, confirm one complete request:

   ```bash
   curl -i -X POST http://127.0.0.1:8000/jobs \
     -H 'Content-Type: application/json' \
     -d '{"duration_seconds":1,"should_fail":false}'
   ```

Stage 7 passes when migrations, all three tests, server startup, and the creation
request succeed exactly as documented.

---

## Stage checkpoints and time budget

- Stage 1 — skeleton and domain: **10 minutes**; cumulative **10**
- Stage 2 — persistence and migration: **20 minutes**; cumulative **30**
- Stage 3 — schemas, repository, service: **35 minutes**; cumulative **65**
- Stage 4 — worker: **20 minutes**; cumulative **85**
- Stage 5 — HTTP runnable checkpoint: **25 minutes**; cumulative **110**
- Stage 6 — three integration tests: **30 minutes**; cumulative **140**
- Stage 7 — documentation and final verification: **10 minutes**; cumulative
  **150**

The application first becomes fully runnable at the end of Stage 5. Stages 1–4
each have a smaller executable verification so defects are found before HTTP
composition.

## Fallback if time is running out

Required behavior must not be cut: migrations, all four endpoints, atomic
claim/cancel, retry rules, startup scheduling of `PENDING` jobs, and
documentation of stranded `RUNNING` jobs remain mandatory.

1. If behind during Stages 1–4:
   - Keep explicit functions and one worker.
   - Do not add base repositories, protocols, configuration classes, generic
     state-machine frameworks, or extra response helpers.
2. If behind at the Stage 5 checkpoint:
   - Use FastAPI's standard `422` body.
   - Keep error responses concise while preserving required `404` and `409`
     statuses.
   - Do not add a list endpoint, health endpoint, pagination, or result payload.
3. If behind during Stage 6:
   - Keep no more than three tests.
   - Reduce to two integration tests only if necessary, combining related
     assertions, but retain coverage of success, failure/retry, and
     cancellation.
4. Preserve the final five minutes:
   - Run `pytest -q`.
   - Run `alembic upgrade head` against a fresh SQLite file.
   - Confirm the README explicitly states that interrupted `RUNNING` jobs are
     not automatically recovered.
