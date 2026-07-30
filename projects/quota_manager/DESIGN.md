# Design Decisions

## Scope

This implementation is optimized for a short backend interview: complete,
readable, testable, and explainable without production-only infrastructure.
It manages one quota and a collection of reservations per tenant.

## Confirmed assumptions

- Configuring a quota implicitly establishes a tenant. There is no separate
  tenant table or tenant lifecycle API.
- Tenant IDs are non-empty client-supplied strings.
- Quota updates are full replacements through `PUT`.
- A quota update below current usage is rejected with `409 Conflict`.
- A reservation without a configured quota is rejected with `404 Not Found`.
- Rejected reservation attempts are not persisted.
- Reservation IDs are server-generated UUID strings.
- New reservations are `ACTIVE`; released reservations remain persisted as
  `RELEASED`.
- Releasing an already released reservation returns `200 OK` and does not
  change usage.
- Zero-resource reservations are accepted because only negative quantities
  are forbidden.
- Lists include active and released reservations ordered by creation time.
- Stored timestamps use UTC semantics. API timestamps are normalized to UTC.
- Current usage is persisted with quota limits.
- SQLite provides sufficient write serialization for this MVP, but this design
  does not claim production-scale concurrency.

## Layer responsibilities

### Domain

`app/domain.py` defines reservation states and business errors. Domain errors
describe business outcomes without HTTP status codes.

### Persistence models

`app/models.py` defines SQLAlchemy mappings and database constraints.

`TenantQuota` stores:

- Tenant ID
- CPU, memory, and GPU limits
- CPU, memory, and GPU usage

`Reservation` stores:

- Unique reservation ID
- Tenant ID
- CPU, memory, and GPU quantities
- `ACTIVE` or `RELEASED` status
- Creation timestamp
- Optional release timestamp

### Repository

`app/repositories.py` contains SQL statements and model persistence. A
repository may flush so generated or database-backed values are available, but
it never commits or owns the outer transaction.

Concrete repositories are used deliberately. There is one SQLAlchemy
implementation, and transaction behavior is a core part of correctness. A
repository protocol plus unit-of-work abstraction would add indirection without
a second implementation or a current testing need.

### Service

`app/services.py` owns business rules and mutation transaction boundaries. Each
mutation uses `session.begin()`, so all related writes commit together or roll
back together.

### HTTP

`app/schemas.py` defines validated Pydantic request and response contracts.
`app/routes.py` maps HTTP requests to service calls. `app/main.py` configures
the application, lifespan, and centralized error handling.

## Engine and session lifecycle

One SQLAlchemy engine is created per application process. The engine is
long-lived and manages reusable database connections.

`SessionLocal` is a factory, not a global session. `get_db()` creates one
session per request and closes it after the response. Sessions are not shared
between concurrent requests.

Application startup executes `SELECT 1` to fail fast when the database cannot
be reached. Shutdown calls `engine.dispose()` to close pooled connections.
Alembic, not application startup, owns schema creation.

## Database invariants

Database constraints reinforce service validation:

- Limits, usage, and reservation quantities cannot be negative.
- Usage cannot exceed its corresponding limit.
- Tenant IDs and reservation IDs cannot be empty.
- An active reservation has no release timestamp.
- A released reservation has a release timestamp.
- Reservations reference a configured tenant quota.

Pydantic rejects negative, fractional, and string resource quantities before
the service executes.

## Transaction design

### Quota replacement

The repository first executes a conditional update:

- Match the tenant.
- Require every new limit to be at least current usage.
- Replace all three limits in one statement.

If no row matches, the service distinguishes between a missing tenant and a
quota below usage. A missing tenant gets a new quota; a quota below usage
returns `409`. The existing quota and usage remain unchanged.

The conditional update avoids a separate read-then-write race for existing
tenants.

### Reservation creation

The repository executes one conditional quota update that:

- Matches only the requested tenant.
- Requires all three requested resources to fit.
- Increments all three usage values together.

The reservation is inserted only if the conditional update succeeds. Usage
increment and reservation insertion occur in the same transaction. Therefore:

- No partial resource allocation is possible.
- A failed insertion rolls back the usage increment.
- Concurrent requests cannot independently pass a stale application-side
  availability check.

If no quota row is updated, the service returns `404` for a missing quota or
`409` with requested and available resources for insufficient quota.

### Reservation release

Release starts with a conditional `ACTIVE` to `RELEASED` update and sets the
release timestamp in the same statement. The update returns the reservation's
resource quantities only to the caller that changed the state.

That caller decrements usage with another guarded update requiring usage to be
at least the released quantities. Both writes occur in one transaction.

Concurrent or repeated callers find the reservation already released and
return its current state without decrementing usage. The guarded usage update
and database constraints prevent negative usage.

## SQLite concurrency

SQLite serializes writes to the database file. Conditional SQL updates make
each quota decision inside the database rather than relying on a stale Python
read. Tests use independent sessions and concurrent threads to verify:

- Successful reservations never exceed quota.
- Concurrent releases decrement usage exactly once.

This is suitable for the interview MVP and a small single-database deployment.
A higher-throughput production service would normally use PostgreSQL and
database-specific row locking or equivalent atomic statements.

## Error handling

Business failures use stable domain codes:

- `QUOTA_NOT_FOUND`
- `QUOTA_BELOW_USAGE`
- `QUOTA_EXCEEDED`
- `RESERVATION_NOT_FOUND`

Pydantic validation failures use `VALIDATION_ERROR`. Framework HTTP failures
also use the common error envelope.

Unexpected `SQLAlchemyError` instances are logged with their traceback and
returned as a safe `500 DATABASE_ERROR`; SQL and internal database details are
not exposed to clients. Transaction context managers roll back failed
mutations.

## Persistence and migrations

The default URL points to `quota_manager.db`, so data survives application
restarts. Alembic owns schema changes.

The initial migration creates both tables and seeds `tenant-1` through
`tenant-5` with identical limits and zero usage. Downgrading removes the tables
and their data; it should only be done against a disposable database.

## Testing strategy

API tests exercise validation, error contracts, quota updates, complete
reservation lifecycle, all-or-nothing allocation, tenant isolation, and
idempotent release.

Each test receives a fresh file-backed SQLite database. This keeps tests
isolated while exercising real SQLAlchemy transactions instead of mocked
repositories. Concurrency tests use independent sessions to model separate
requests.

## Deliberately excluded

- Authentication and authorization
- Separate tenant lifecycle management
- Reservation expiry and background cleanup
- Idempotency keys for reservation creation
- Rejected-attempt and quota-change audit history
- Pagination and advanced filtering
- Arbitrary resource types
- Rate limiting, metrics, and distributed tracing
- Redis, queues, Docker, and distributed locks
- Horizontal scaling and production database infrastructure
