# Generic Backend Interview File-Creation Mental Map

> A reusable end-to-end template for turning an unfamiliar set of backend requirements into a working, persistent, interview-ready Python application.
>
> This template is intentionally **use-case neutral**. Replace placeholders such as `<resource>`, `<action>`, and `<external_system>` with the language from the problem statement.
>
> It is designed primarily for **FastAPI + SQLAlchemy** interview projects, but the responsibility order also applies to CLI, event-driven, and service-based applications. Not every project needs every file. Follow the decision gates and create a file only when the requirement introduces that responsibility.

---

# 1. The governing rule

Do not begin by reproducing a large final folder tree.

Use this loop throughout the interview:

```text
Read one requirement
        ↓
Extract the responsibility and invariant
        ↓
Decide which layer should own it
        ↓
Create or modify the smallest appropriate file
        ↓
Wire one vertical path end to end
        ↓
Run or manually verify it
        ↓
Continue to the next requirement
```

The default build progression is:

```text
Requirements and assumptions
    ↓
API/event contract
    ↓
Runnable application shell
    ↓
Domain vocabulary and rules
    ↓
Persistence/integration boundaries
    ↓
Use-case orchestration
    ↓
Transport adapters and dependency wiring
    ↓
Error translation and transactions
    ↓
Manual end-to-end verification
    ↓
Lean high-value tests
    ↓
Migrations and documentation
    ↓
Final demo and trade-off discussion
```

## Priority order under time pressure

```text
Working vertical slice
    > correct business rules
    > correct persistence/transaction boundary
    > expected error behaviour
    > clear design explanation
    > lean integration tests
    > optional abstractions and polish
```

---

# 2. Scope and non-goals

This template fits requirements involving combinations of:

- HTTP APIs
- CRUD or workflow operations
- Database persistence
- External service calls
- Authentication or authorisation
- Background processing
- Files or object storage
- Caching
- Queues or events
- Scheduled work

It is not a command to create every possible layer. A simple read-only API may need only:

```text
main.py
schemas.py
service.py
routers/<resource>.py
```

A persistence-heavy workflow may need the complete path:

```text
router
→ schema
→ service/use case
→ repository protocol
→ SQL repository
→ ORM model
→ database
```

A third-party integration may replace the repository path with:

```text
router or worker
→ schema/event model
→ service/use case
→ gateway protocol
→ external client adapter
```

---

# 3. Status key

| Label | Meaning |
|---|---|
| **Create** | Add the file for the first time. |
| **Modify** | Return to an existing file to wire a new responsibility. |
| **Generate** | A tool creates the initial file or directory. |
| **Conditional** | Create only when the requirements justify it. |
| **Defer** | Valuable, but not required for the first working vertical slice. |
| **Skip** | Do not create for the current project. |

---

# 4. Step zero: convert requirements into a build plan

Before writing application code, extract the following.

## 4.1 Actors

```text
Who calls the system?
Who owns the data?
Who is allowed to perform each action?
Are there administrators, users, services, or anonymous callers?
```

## 4.2 Capabilities

Rewrite requirements as verbs:

```text
create
retrieve
list
update
cancel
delete
process
approve
retry
upload
notify
```

These verbs usually become service/use-case methods and transport endpoints.

## 4.3 Core entities and value objects

Identify the nouns:

```text
<Resource>
<User>
<Order>
<Job>
<Payment>
<Booking>
<Document>
```

Then identify constrained values:

```text
identifier
status
amount
email
URL
date range
priority
quantity
```

## 4.4 Invariants

Write rules that must always remain true:

```text
Identifiers are unique.
An amount cannot be negative.
A completed operation cannot be cancelled.
An expiration time must be in the future.
Only an owner may update a resource.
A retry count cannot exceed the configured limit.
```

Invariants determine whether logic belongs in:

```text
domain model
service/use case
database constraint
authorisation dependency
```

## 4.5 Inputs and outputs

Write the contract before internal implementation:

```text
HTTP method/path or incoming event
request fields
response fields
success status
expected failures
side effects
```

## 4.6 Non-functional requirements

Look for phrases such as:

```text
persist across restarts
handle concurrent requests
avoid duplicates
process asynchronously
support retries
respond quickly
secure sensitive fields
provide audit history
```

These determine infrastructure and transaction decisions.

## 4.7 Explicit exclusions

State what is intentionally outside the interview implementation:

```text
No authentication unless requested.
No distributed cache.
No production deployment setup.
No full-text search.
No complex retry scheduler.
No exhaustive test suite.
```

### Exit condition

You can describe the system in one sentence and list the minimum working vertical slice.

---

# 5. Requirement-to-file translation table

| Requirement or responsibility | Default owner |
|---|---|
| Environment/configuration | `app/config.py` |
| Shared stable constants | `app/constants.py` |
| Domain state and object-level invariants | `app/models.py` or `app/domain/models.py` |
| Application-specific failures | `app/exceptions.py` |
| Use-case orchestration | `app/service.py` or `app/use_cases/<action>.py` |
| Incoming/outgoing HTTP validation | `app/schemas.py` |
| Reusable path/query/header types | `app/api_types.py` |
| HTTP routes | `app/routers/<resource>.py` |
| HTTP exception translation | `app/exception_handlers.py` |
| Dependency construction | `app/dependencies.py` |
| Database engine/session | `app/database.py` |
| ORM/table definitions | `app/database_models.py` |
| Domain ↔ ORM conversion | `app/persistence_mappers.py` |
| Persistence contract | `app/repository_protocol.py` or `app/ports.py` |
| SQL implementation | `app/sql_repository.py` or `app/repositories/<resource>.py` |
| External-system contract | `app/gateway_protocol.py` or `app/ports.py` |
| External API implementation | `app/integrations/<external_system>.py` |
| Authentication/security | `app/security.py`, `app/auth.py`, dependencies |
| Background work | `app/jobs/`, `app/tasks/`, or `app/workers/` |
| Queue/event messages | `app/events.py` or `app/event_schemas.py` |
| Logging setup | `app/logging_config.py` |
| Versioned schema changes | `alembic.ini`, `migrations/` |
| High-value behaviour verification | `tests/integration/` |
| Unit-level complex rule verification | `tests/unit/` |
| Runbook and trade-offs | `README.md` |

---

# 6. Architecture decision gates

Run these gates before creating infrastructure files.

## Gate A — Is there an HTTP interface?

### Yes

Create eventually:

```text
app/main.py
app/schemas.py
app/dependencies.py
app/routers/<resource>.py
app/exception_handlers.py
```

### No

Use the relevant entry adapter instead:

```text
CLI        → app/cli.py
Worker     → app/worker.py
Consumer   → app/consumers/<event>.py
Scheduler  → app/jobs/<job>.py
```

The domain and use-case layers remain reusable.

---

## Gate B — Must data survive process restarts?

### Yes

Create:

```text
app/database.py
app/database_models.py
app/persistence_mappers.py       # when domain and ORM models are separate
app/repository_protocol.py       # when service should not know SQLAlchemy
app/sql_repository.py
migrations/
```

### No

Start with an in-memory adapter or plain service state. Do not add SQLAlchemy merely because the template contains it.

---

## Gate C — Are there meaningful business rules?

### Yes

Create a storage-independent domain model and service/use-case layer:

```text
app/models.py
app/exceptions.py
app/service.py
```

### No, it is trivial CRUD

A lean implementation may use:

```text
schemas.py
repository.py
routers/<resource>.py
```

State the trade-off. Do not manufacture domain complexity.

---

## Gate D — Does the system call an external service?

### Yes

Create a boundary:

```text
app/gateway_protocol.py
app/integrations/<external_system>.py
```

Keep credentials, timeouts, HTTP details, and vendor payloads out of the service.

### No

Skip integration files.

---

## Gate E — Is work asynchronous or long-running?

### Yes

Create only the needed path:

```text
app/events.py
app/tasks/<task>.py
app/workers/<worker>.py
```

The synchronous request should usually enqueue or schedule work rather than perform it inline.

### No

Keep the workflow synchronous.

---

## Gate F — Is authentication or ownership required?

### Yes

Create:

```text
app/security.py or app/auth.py
app/dependencies.py              # current-user dependency
```

Authorisation checks normally belong in the use case/service, with identity obtained at the transport boundary.

### No

Do not add placeholder authentication.

---

## Gate G — Can concurrent requests violate correctness?

### Yes

Identify the final authority:

```text
unique constraint
conditional UPDATE
row lock
optimistic version column
idempotency key
transaction isolation
```

Do not rely only on application-level `exists()` checks or Python read-modify-write logic.

---

# 7. Default end-to-end file-creation sequence

The following is the recommended order for a persistent API interview project. Conditional steps may be skipped.

---

## Step 1 — Record the contract

### Create or modify

```text
README.md
```

Initially include only:

```text
Problem summary
Assumptions
Endpoints or incoming events
Success and error semantics
Out-of-scope items
```

### Why first

The contract controls the implementation. It prevents creating abstractions before understanding required behaviour.

### Exit condition

The interviewer can confirm or correct your assumptions.

---

## Step 2 — Create project metadata and package skeleton

### Create

```text
pyproject.toml
.gitignore
.env.example
app/__init__.py
app/routers/__init__.py            # HTTP only
```

### Minimum dependencies for a FastAPI + SQLAlchemy project

```text
fastapi[standard]
pydantic-settings
sqlalchemy
```

### Development dependencies

```text
pytest
httpx
alembic
ruff                              # optional
```

### `.gitignore`

Ignore at least:

```text
.env
*.db
*.sqlite*
__pycache__/
.pytest_cache/
.ruff_cache/
*.egg-info/
```

### Exit condition

The project installs and the package imports.

---

## Step 3 — Centralise configuration

### Create

```text
app/config.py
```

### Owns

```text
Settings
get_settings()
```

### Possible settings

```text
app_name
app_version
environment
log_level
database_url
external service URLs/timeouts
feature switches
```

### Rules

- Read configuration from environment variables.
- Keep secrets out of source code.
- Do not load settings from `main.py` inside low-level modules.
- Use one clear settings owner.

### Exit condition

A small command can load and print non-sensitive settings successfully.

---

## Step 4 — Create the smallest runnable entry point

### Create

```text
app/main.py
```

### Initial responsibility

```text
Create application
Add lifespan if infrastructure needs startup/shutdown
Expose GET /health
```

### Do not add yet

```text
Every route
Every dependency
Every handler
Every integration
```

### Verify

```bash
uvicorn app.main:app --reload
```

```text
GET /health → 200
```

### Why early

A runnable shell creates a stable feedback loop. Later layers are integrated incrementally.

---

## Step 5 — Create neutral shared constants only when justified

### Conditional create

```text
app/constants.py
```

### Appropriate contents

```text
validation bounds
reserved names
stable status values
retry limits that are truly code constants
```

### Avoid

- Environment-specific values; put them in `config.py`.
- Large unrelated collections.
- Values used by only one function.

---

## Step 6 — Define the domain vocabulary

### Create

```text
app/models.py
```

or, for a larger problem:

```text
app/domain/models.py
app/domain/value_objects.py
```

### Owns

```text
Core entities
Value objects
Object-level invariants
State transitions local to an entity
```

### Examples of object-level behaviour

```text
is_expired()
can_transition_to(status)
remaining_quantity()
mark_completed()
```

### Rules

The domain should not import:

```text
FastAPI
SQLAlchemy
HTTP clients
queue SDKs
```

### Skip/semi-skip condition

For trivial CRUD with no meaningful rules, a separate rich domain model may be unnecessary. State this decision rather than forcing one.

---

## Step 7 — Define the application exception vocabulary

### Create

```text
app/exceptions.py
```

### Examples

```text
ResourceNotFoundError
DuplicateResourceError
InvalidStateTransitionError
PermissionDeniedError
ExternalDependencyError
ConflictError
```

### Why before HTTP handlers

The core application should express failures in its own language. Transport adapters translate them later.

```text
Database/vendor error
    ↓ adapter translation
Application exception
    ↓ HTTP/event adapter translation
Public response or retry action
```

---

## Step 8 — Define outbound contracts/ports

### Conditional create

For persistence:

```text
app/repository_protocol.py
```

For multiple outbound dependencies:

```text
app/ports.py
```

For a specific external service:

```text
app/gateway_protocol.py
```

### Owns

Only the operations the use case needs:

```text
save(resource)
get(resource_id)
list(...)
delete(resource_id)
send_notification(...)
charge_payment(...)
store_file(...)
```

### Correct dependency direction

```text
Service/use case
        ↓ depends on contract
Port/Protocol
        ↑ implemented by
SQL repository / API client / queue adapter
```

### When to skip

For a tiny one-file exercise or trivial CRUD, direct dependency on a repository class can be acceptable. Avoid an interface with no architectural purpose.

---

## Step 9 — Create the database foundation

### Conditional create

```text
app/database.py
```

### Owns

```text
Engine
SessionFactory
Connectivity check
Engine disposal
```

### Rules

```text
One Engine per application process
One Session per request/use-case unit of work
No global Session object
No repository hidden inside database.py
```

### Exit condition

A `SELECT 1` or equivalent connectivity check succeeds.

---

## Step 10 — Define persistence models and constraints

### Conditional create

```text
app/database_models.py
```

or, for several aggregates:

```text
app/db_models/<resource>.py
```

### Owns

```text
Declarative Base
ORM entities
Columns
Primary keys
Foreign keys
Unique constraints
Check constraints
Indexes
```

### Constraint rule

Use the database as the final authority for cross-request integrity:

```text
uniqueness
non-negative values
foreign-key existence
idempotency keys
valid status sets where appropriate
```

### Domain versus ORM decision

Use separate models when:

- The domain has meaningful behaviour.
- The ORM has internal fields not exposed to the core.
- Storage may change.
- Vendor-specific persistence details should not leak.

Combining them may be acceptable for a small CRUD service. Explain the trade-off.

---

## Step 11 — Create persistence mappers

### Conditional create

```text
app/persistence_mappers.py
```

### Create only when

```text
Domain model ≠ ORM model
```

### Owns

```text
to_record(domain)
to_domain(record)
```

### Rules

- Do not expose ORM records to the service or API.
- Normalise datetimes and enums at the boundary.
- Keep database-only identifiers out of the domain unless genuinely required.

---

## Step 12 — Implement outbound adapters

### Database adapter

Create:

```text
app/sql_repository.py
```

or:

```text
app/repositories/<resource>.py
```

### External API adapter

Create:

```text
app/integrations/<external_system>.py
```

### Object storage adapter

Create:

```text
app/integrations/storage.py
```

### Adapter responsibilities

```text
Translate domain objects to provider/storage shapes
Execute I/O
Translate known low-level errors into application exceptions
Do not own HTTP route decisions
Do not own unrelated business workflows
```

### Transaction rule for SQL repositories

Default interview-optimised approach:

```text
Repository adds/updates/deletes and may flush
Request/use-case boundary commits or rolls back
```

Avoid committing inside every repository method unless each method is deliberately its own complete transaction.

---

## Step 13 — Implement the service/use-case layer

### Create

```text
app/service.py
```

For a larger requirement set:

```text
app/use_cases/create_<resource>.py
app/use_cases/update_<resource>.py
app/use_cases/process_<resource>.py
```

### Owns

```text
Application workflows
Cross-entity rules
Authorisation decisions using supplied identity
Calls to repositories/gateways
Retry decisions
Transaction-level intent
```

### Typical method shape

```text
validate business preconditions
    ↓
load required state
    ↓
apply domain rule
    ↓
persist or call outbound adapter
    ↓
return domain result
```

### The service should not know

```text
HTTP status codes
FastAPI Request/Response
SQLAlchemy query syntax
vendor HTTP payload details
```

### Exit condition

The core use case works from a Python script or REPL with real or simple test adapters.

---

## Step 14 — Define transport schemas

### HTTP create

```text
app/schemas.py
```

### Owns

```text
Request models
Response models
Public error schema
Boundary validation
Serialisation rules
```

### Optional create

```text
app/api_types.py
```

Use for reusable annotated path/query/header types.

### Boundary rule

```text
Pydantic validates transport input
Service validates business rules
Database enforces final relational integrity
```

Do not rely on only one layer for every kind of validation.

---

## Step 15 — Create response/transport mappers when needed

### Conditional create

```text
app/mappers.py
```

### Create when

- Response fields differ from domain fields.
- URLs or derived fields must be constructed.
- Several routes repeat conversion logic.

### Skip when

A response model can be created clearly in one line without duplication.

---

## Step 16 — Create dependency wiring

### HTTP create

```text
app/dependencies.py
```

### Owns

```text
Request-scoped database session
Repository construction
Gateway/client construction
Service/use-case construction
Current user or security context
```

### Default database lifetime

```text
Request begins
    ↓
Create Session
    ↓
Create repository/service graph
    ↓
Execute route/use case
    ↓
Success → commit
Failure → rollback
    ↓
Close Session
```

### Rules

- The engine is application-scoped.
- The session is request/use-case-scoped.
- Do not reuse one global session across requests.
- Commit should complete before a success response is irreversibly sent.

---

## Step 17 — Create the first vertical route

### Create

```text
app/routers/<resource>.py
```

Start with the smallest valuable vertical slice, usually:

```text
create + retrieve
```

or:

```text
submit + get status
```

### Route responsibility

```text
Receive validated transport data
Call one service/use case
Map result to response
Set transport-specific headers/status
```

### Route must not contain

```text
SQL queries
transaction ownership
large business workflows
vendor SDK calls
```

### Modify

```text
app/main.py
```

Register the router only after it imports and its first path works.

### Exit condition

One real request travels through every required layer and returns the correct result.

---

## Step 18 — Add remaining routes incrementally

### Modify/create

```text
app/routers/<resource>.py
app/routers/<second_resource>.py
```

Add one behaviour at a time:

```text
retrieve
list
update
delete
special action
```

After each route:

```text
run request
inspect response
inspect persisted side effect
fix before continuing
```

Do not create every endpoint and debug them all at the end.

---

## Step 19 — Translate application errors

### Create

```text
app/exception_handlers.py
```

### Owns

```text
Application exception → HTTP status/public error
Request validation error → consistent public shape
Unknown exception → safe 500 response
```

### Example mapping

```text
NotFoundError          → 404
Duplicate/Conflict     → 409
Invalid business input → 400
Permission denied      → 403
Expired/unavailable    → 410 or domain-appropriate status
External dependency    → 502 or 503
Unexpected failure     → 500
```

### Modify

```text
app/main.py
```

Register handlers centrally.

### Rule

Do not expose raw SQL, stack traces, secrets, or vendor internals to clients.

---

## Step 20 — Add concurrency and idempotency protections

### Modify the owning layer

Possible files:

```text
app/database_models.py
app/sql_repository.py
app/service.py
app/schemas.py
```

### Common patterns

#### Uniqueness

```text
Database UNIQUE constraint
+ adapter translation to conflict
```

#### Counter or quantity update

Prefer:

```sql
value = value + 1
```

or a conditional update, rather than Python read-modify-write.

#### State transition

```text
UPDATE ...
WHERE id = ? AND status = expected_status
```

Check affected row count.

#### Idempotent submission

```text
idempotency_key UNIQUE
request result stored/reused
```

#### Generated-value collision retry

Use a bounded retry and, when needed, a savepoint so one failed insert does not invalidate the whole transaction.

### Rule

An application pre-check can improve messaging, but the database or idempotency store must be the final concurrency-safe authority.

---

## Step 21 — Add external integrations only after the core path works

### Conditional create

```text
app/integrations/<external_system>.py
```

### Include

```text
base URL from settings
timeouts
authentication headers
request/response mapping
known error translation
```

### Optional protocol

```text
app/gateway_protocol.py
```

### Interview-optimised rule

Use a real adapter interface but a simple deterministic fake during early local verification if the external system is unavailable.

### Avoid

- Calling third-party APIs directly from routes.
- Hard-coded credentials.
- Unbounded timeouts.
- Returning vendor response bodies as your public API contract.

---

## Step 22 — Add authentication and authorisation when required

### Conditional create

```text
app/security.py
app/auth.py
```

### Modify

```text
app/dependencies.py
app/service.py
app/routers/<resource>.py
```

### Responsibility split

```text
security/auth module
    verifies token/credential and produces identity

dependency
    supplies current identity to route/use case

service/use case
    decides whether that identity may perform the action
```

Do not bury ownership rules only in route code.

---

## Step 23 — Add background processing when required

### Conditional create

```text
app/events.py
app/tasks/<task>.py
app/workers/<worker>.py
```

### Request path

```text
validate request
    ↓
create durable job/event record or publish message
    ↓
return accepted/job identifier
```

### Worker path

```text
consume job/event
    ↓
run service/use case
    ↓
record success/failure
    ↓
retry according to policy
```

### Correctness concerns

```text
idempotency
retry limits
dead-letter/failure handling
visibility/status
timeouts
```

Do not introduce a queue for work that comfortably completes inside the request and has no asynchronous requirement.

---

## Step 24 — Add logging after the core path is visible

### Conditional create

```text
app/logging_config.py
```

### Modify

```text
app/main.py
app/service.py
app/integrations/*.py
```

### Log useful events

```text
application start/stop
use-case success/failure
resource identifier
external dependency latency/failure
retry attempts
```

### Do not log

```text
passwords
tokens
complete sensitive payloads
unnecessary personal data
```

Keep logging structured and purposeful. Do not spend interview time building a complete observability platform.

---

## Step 25 — Manually verify the full lifecycle

Before automated tests, run the real application and prove the critical path.

Generic sequence:

```text
Create/submit resource
    ↓
Retrieve resource
    ↓
Perform important action
    ↓
Verify changed state or side effect
    ↓
Restart application if persistence matters
    ↓
Retrieve again
    ↓
Trigger one expected error
    ↓
Delete/cancel if required
```

Inspect both:

```text
HTTP/event result
Persisted state or outbound effect
```

### Exit condition

The minimum promised workflow works end to end without relying on mocks.

---

## Step 26 — Add lean high-value tests

### Create

```text
tests/integration/test_<critical_workflow>.py
```

### Default interview test budget

Add one to three tests covering the newest/highest-risk behaviour:

```text
1. Successful end-to-end lifecycle
2. Most important integrity/conflict behaviour
3. Optional critical failure/authorisation behaviour
```

### Add unit tests only for genuinely complex isolated logic

```text
tests/unit/test_<rule>.py
```

Examples:

```text
pricing calculation
state transition matrix
retry backoff calculation
permission policy
```

### Avoid spending the interview on

```text
large fixture factories
every getter/setter
every validation permutation
mock-heavy repository method tests
full coverage targets
```

### Testing principle

Test the **new risk surface**, not every line.

---

## Step 27 — Add versioned migrations

### Conditional generate/create

```text
alembic.ini
migrations/
```

### Configure

```text
Database URL from app settings
Target metadata from ORM Base.metadata
```

### Generate and review

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### Review every generated migration

Confirm:

```text
correct tables and columns
constraints and indexes
data-preserving behaviour
downgrade implications
```

### Ownership rule

Once Alembic owns schema evolution, remove runtime `create_all()` from application startup.

### Time-pressure exception

If migrations are not required and time is almost exhausted, use `create_all()` temporarily, document Alembic as the next step, and prioritise a working system. Do not pretend this is production migration management.

---

## Step 28 — Finish the README

### Modify

```text
README.md
```

### Include

```text
Problem summary
Assumptions
Architecture diagram
Setup/install commands
Environment variables
Database migration command
Run command
Endpoint/event examples
Test command
Major design decisions
Known limitations
What you would add next
```

The README should enable the interviewer to run the project without reading your mind.

---

## Step 29 — Final code-quality pass

Run:

```text
formatter/linter
type checker if already configured
tests
manual smoke flow
```

Search for:

```text
hard-coded secrets
unused imports
debug prints
raw exception leakage
open sessions/files
missing rollback
route-level SQL
unbounded external calls
ambiguous names
```

Do not perform a large refactor immediately before the demo.

---

## Step 30 — Prepare the interview walkthrough

Explain in this order:

```text
1. Working behaviour
2. Request/event lifecycle
3. Core business rules
4. Persistence/integration boundary
5. Transaction and concurrency decisions
6. Error translation
7. Tests selected
8. Known limitations
9. Production evolution
```

Avoid beginning with a long tour of every file.

---

# 8. The default dependency direction

```text
Transport adapter
(router / CLI / consumer / worker)
        ↓
Transport schema or event model
        ↓
Service / use case
        ↓
Domain model and application exceptions
        ↓
Port / protocol
        ↑
Outbound adapter
(SQL repository / external client / storage / queue)
        ↓
Infrastructure
(database / HTTP / filesystem / broker)
```

## Import-direction rule

Lower-level application logic should not import higher-level delivery mechanisms.

Good:

```text
router imports service
service imports domain + protocol
SQL repository imports protocol/domain/ORM
```

Avoid:

```text
domain imports FastAPI
service imports router schemas
repository imports main.py
database imports dependencies.py
```

---

# 9. Recommended default folder tree

This is a **menu**, not a checklist. Delete conditional files that the problem does not need.

```text
project/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── alembic.ini                         # conditional
├── migrations/                         # conditional
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                         # HTTP entry point
│   ├── config.py
│   ├── constants.py                    # conditional
│   ├── models.py                       # domain models
│   ├── exceptions.py
│   ├── service.py                      # or use_cases/
│   ├── ports.py                        # conditional
│   ├── repository_protocol.py          # conditional alternative
│   ├── gateway_protocol.py             # conditional alternative
│   ├── database.py                     # conditional
│   ├── database_models.py              # conditional
│   ├── persistence_mappers.py          # conditional
│   ├── sql_repository.py               # conditional
│   ├── schemas.py                      # HTTP only
│   ├── api_types.py                    # conditional
│   ├── mappers.py                      # conditional
│   ├── dependencies.py                 # HTTP DI/wiring
│   ├── exception_handlers.py           # HTTP only
│   ├── logging_config.py               # conditional
│   ├── security.py                     # conditional
│   ├── events.py                       # conditional
│   ├── routers/
│   │   ├── __init__.py
│   │   └── <resource>.py
│   ├── integrations/                   # conditional
│   │   └── <external_system>.py
│   ├── tasks/                          # conditional
│   │   └── <task>.py
│   └── workers/                        # conditional
│       └── <worker>.py
└── tests/
    ├── unit/                            # conditional
    │   └── test_<complex_rule>.py
    └── integration/
        └── test_<critical_workflow>.py
```

---

# 10. Lean versus expanded organisation

## Lean interview layout

Prefer a flat `app/` while the project is small:

```text
app/models.py
app/service.py
app/sql_repository.py
app/schemas.py
```

This reduces navigation and import overhead.

## Expand when responsibilities multiply

Move to packages only when needed:

```text
app/domain/
app/use_cases/
app/repositories/
app/integrations/
app/api/
```

Do not create enterprise folder depth for five small files.

---

# 11. Generic vertical-slice checklist

For each important capability, verify this chain:

```text
Requirement
    ↓
Input contract
    ↓
Business rule/use case
    ↓
Outbound port
    ↓
Real adapter
    ↓
Transaction/side effect
    ↓
Output/error contract
    ↓
Manual verification
```

Example placeholder:

```text
POST /<resources>
    ↓
Create<Resource>Request
    ↓
<Resource>Service.create()
    ↓
<Resource>Repository.save()
    ↓
SQL INSERT + constraint check
    ↓
commit
    ↓
201 Create<Resource>Response
```

Do not move to the next major feature while this chain is broken.

---

# 12. File creation rules that prevent overengineering

## Create a new file when

- It owns a distinct responsibility.
- It introduces an infrastructure boundary.
- It prevents a circular import.
- The same conversion/logic is repeated.
- It needs independent lifecycle or configuration.
- It is likely to change for a different reason than the current file.

## Keep code in the current file when

- The helper is small and used once.
- Splitting would create a file containing only a trivial wrapper.
- The responsibility is still cohesive.
- The interview would become harder to navigate with no design benefit.

## Create a protocol/interface when

- The core must not depend on a concrete infrastructure technology.
- There are or may reasonably be multiple adapters.
- Test substitution materially benefits from the boundary.
- The dependency represents an external side effect.

## Skip a protocol when

- It merely mirrors one trivial class with no decoupling benefit.
- The exercise is too small for the abstraction to clarify anything.

## Create a mapper when

- Domain, persistence, and transport shapes differ.
- Internal fields must not leak.
- Conversion is repeated.

## Skip a mapper when

- The two shapes are intentionally identical and conversion is trivial.

---

# 13. Transaction ownership template

Use one clear owner for the outer transaction.

## Recommended request-scoped pattern

```text
Dependency/unit of work opens session
    ↓
Repository executes and flushes
    ↓
Service completes the use case
    ↓
Success → outer commit
Failure → outer rollback
    ↓
Session closes
```

## Why repositories normally should not commit

A use case may require multiple operations:

```text
create resource
write audit record
reserve inventory
publish outbox event
```

If the first repository commits independently, the complete workflow can no longer roll back as one unit.

## Valid exception

A repository method may own a commit when it is explicitly the complete transaction boundary and this is intentional. State that choice clearly.

---

# 14. Error ownership template

```text
Low-level infrastructure error
    ↓ adapter recognises known condition
Application exception
    ↓ transport adapter
HTTP status / event retry / CLI message
```

Example:

```text
Database IntegrityError
    ↓ SQL repository
DuplicateResourceError
    ↓ HTTP handler
409 Conflict
```

Unknown low-level failures should remain unexpected, be logged safely, and produce a generic public failure.

---

# 15. Testing decision template

Ask three questions:

```text
What is newly risky in this implementation?
What failure would invalidate the whole design?
What behaviour is difficult to prove manually every time?
```

Then select the smallest set of high-value tests.

## Common integration-test candidates

- Data persists across independent sessions.
- A database uniqueness constraint becomes a conflict response.
- An authenticated user cannot access another user’s resource.
- A state transition is atomically protected.
- An external-client failure becomes the expected application error.
- A queued job is idempotent when delivered twice.

## Common unit-test candidates

- Complex calculation.
- State machine.
- Permission policy.
- Retry/backoff rule.
- Parsing or transformation with many edge cases.

---

# 16. Three-hour interview time box

Use this as a default and adapt to the problem.

| Approx. time | Focus | Exit condition |
|---:|---|---|
| 0–15 min | Clarify requirements, actors, invariants, contract | Assumptions and minimum vertical slice are explicit. |
| 15–30 min | Project setup, settings, runnable shell | Application starts and health check works. |
| 30–60 min | Domain vocabulary, exceptions, DB/integration boundary | Core types and outbound contract exist. |
| 60–105 min | Real adapter and service/use case | Main workflow works from Python. |
| 105–145 min | Schemas, dependencies, first routes/entry adapters | End-to-end minimum flow works. |
| 145–165 min | Remaining critical routes, errors, concurrency fixes | Promised workflow is stable. |
| 165–180 min | Lean tests, migrations/README, final demo prep | Highest-risk behaviour is covered and project is runnable. |

The time box is not a mandate. If requirements are integration-heavy, move time from additional routes to the external adapter and failure behaviour.

---

# 17. Time-pressure fallback levels

## Level 1 — Full interview-optimised solution

```text
Domain/service separation
Persistence/integration port
Real adapter
Request-scoped transaction
Central error translation
One to three integration tests
Migrations
README
```

## Level 2 — Working layered solution

```text
Service
Concrete repository/client
Schemas/routes
Correct transaction
Manual verification
One critical test
```

Defer protocols, dedicated mappers, and extensive documentation when they do not affect correctness.

## Level 3 — Minimum complete vertical slice

```text
One main endpoint/action
Real persistence or required integration
Expected success and one critical error
Runnable setup instructions
```

Explicitly document the next steps. A smaller complete system is stronger than a large incomplete architecture.

---

# 18. Common mistakes and corrections

## Mistake: Creating the final folder tree before the first request works

**Correction:** Build one vertical slice and let new responsibilities justify new files.

## Mistake: Putting SQL in routes

**Correction:** Keep I/O in an adapter/repository and workflow logic in a service/use case.

## Mistake: Creating a global SQLAlchemy Session

**Correction:** Share the engine; scope the session to one request or unit of work.

## Mistake: Committing in every repository method

**Correction:** Let one outer use-case/request boundary own commit and rollback.

## Mistake: Checking uniqueness only with `exists()`

**Correction:** Add a database unique constraint and translate its violation.

## Mistake: Using Python read-modify-write for concurrent counters/state

**Correction:** Use an atomic or conditional database update.

## Mistake: Mixing Pydantic, domain, and ORM models without deciding

**Correction:** Either separate them deliberately or combine them deliberately for a trivial CRUD project. Explain the trade-off.

## Mistake: Calling external systems directly from routes

**Correction:** Create a client/gateway adapter and let the service coordinate it.

## Mistake: Adding extensive tests before the workflow works

**Correction:** Manually prove the vertical path, then test the highest-risk behaviour.

## Mistake: Keeping both `create_all()` and Alembic as schema owners

**Correction:** Once migrations are introduced, make Alembic the single schema-evolution owner.

## Mistake: Claiming production readiness

**Correction:** State limitations such as authentication, scale, retries, monitoring, database choice, and deployment strategy honestly.

---

# 19. Final project review checklist

## Requirements

- [ ] Actors and ownership are understood.
- [ ] Minimum required capabilities work.
- [ ] Assumptions are documented.
- [ ] Out-of-scope items are explicit.

## Architecture

- [ ] Each file has one clear responsibility.
- [ ] Core logic does not depend on FastAPI or SQLAlchemy unnecessarily.
- [ ] Outbound I/O sits behind a repository/gateway boundary when useful.
- [ ] Dependency direction is inward toward use cases/domain.
- [ ] No circular imports are present.

## Persistence and transactions

- [ ] Engine lifecycle is application-scoped.
- [ ] Session/unit of work is request/use-case-scoped.
- [ ] Commit and rollback have one clear owner.
- [ ] Database constraints protect cross-request integrity.
- [ ] Concurrency-sensitive updates are atomic or conditional.
- [ ] Migrations have one clear owner if used.

## Transport

- [ ] Incoming data is validated.
- [ ] Business errors map to deliberate public responses.
- [ ] Unknown errors do not leak internals.
- [ ] Routes remain thin.
- [ ] Status codes and headers match the contract.

## Integrations

- [ ] Credentials and endpoints come from settings.
- [ ] Timeouts are bounded.
- [ ] Vendor payloads do not leak into the public contract.
- [ ] Known vendor failures are translated.
- [ ] Retry/idempotency behaviour is explicit when required.

## Testing

- [ ] The main lifecycle is manually verified.
- [ ] Highest-risk behaviour has focused automated coverage.
- [ ] Tests do not mutate the developer/production database.
- [ ] Test doubles replace only genuine external boundaries.

## Delivery

- [ ] Install, migration, run, and test commands work.
- [ ] No secrets or local database files are committed.
- [ ] README explains design decisions and limitations.
- [ ] Final demonstration follows the business workflow, not the folder tree.

---

# 20. The reusable interview script

When you receive a new problem, speak and act in this sequence:

```text
1. “I’ll first clarify actors, invariants, and the minimum successful workflow.”

2. “I’ll write the API/event contract and assumptions before choosing files.”

3. “I’ll create a runnable shell so every later change can be verified incrementally.”

4. “I’ll model the core business vocabulary without coupling it to FastAPI or SQLAlchemy.”

5. “I’ll define the outbound operations the use case needs, then implement the real adapter.”

6. “I’ll keep one clear transaction boundary and use the database as the final integrity authority.”

7. “I’ll expose one complete vertical slice before adding the remaining endpoints.”

8. “I’ll translate expected failures centrally and verify the full lifecycle manually.”

9. “I’ll add only the tests that cover the highest-risk new behaviour.”

10. “I’ll finish with migrations/setup instructions, known limitations, and production next steps.”
```

---

# 21. One-page condensed mental map

```text
REQUIREMENTS
├── actors and permissions
├── capabilities
├── entities and invariants
├── inputs/outputs/errors
├── persistence/integration needs
└── exclusions
        ↓
CONTRACT
├── endpoints/events
├── schemas
└── success/error semantics
        ↓
SKELETON
├── pyproject.toml
├── config.py
└── main.py + health
        ↓
CORE
├── models.py
├── exceptions.py
├── service.py/use_cases
└── ports/protocols when useful
        ↓
ADAPTERS
├── database.py
├── database_models.py
├── persistence_mappers.py
├── sql_repository.py
└── integrations/<system>.py
        ↓
WIRING
├── dependencies.py
├── schemas.py
├── routers/<resource>.py
└── exception_handlers.py
        ↓
CORRECTNESS
├── transaction boundary
├── constraints
├── atomic/conditional updates
├── idempotency/retries
└── safe error translation
        ↓
VERIFY
├── manual lifecycle
├── focused integration tests
└── unit tests only for complex rules
        ↓
DELIVER
├── Alembic migrations when persistent
├── README
├── limitations
└── final business-flow demo
```

---

# 22. Final principle

The file-creation mental map is not about memorising filenames.

It is about repeatedly answering:

```text
What responsibility did this requirement introduce?
Which layer should own it?
What is the smallest file/change that makes one real workflow work?
How will I prove it before moving on?
```

Following that reasoning produces a correct project structure even when the use case, entities, endpoints, and integrations are completely different.
