# TinyURL V3 Interview File-Creation Mental Map

> An end-to-end build sequence for implementing the complete TinyURL project **directly in V3 mode** during an interview.
>
> This is **not** organised as V1 → V2 → V3. It assumes you receive the requirements once and immediately build a persistent FastAPI application using SQLAlchemy, SQLite, request-scoped transactions, lean integration tests, and Alembic.

---

## 1. How to use this mental map

Do not start by creating every file from the final folder tree.

Follow this loop:

```text
Understand one requirement
        ↓
Identify the responsibility it introduces
        ↓
Create the smallest file that owns that responsibility
        ↓
Wire it into the existing path
        ↓
Run or manually verify the new behaviour
        ↓
Continue to the next requirement
```

The desired interview progression is:

```text
Requirements
    ↓
Runnable FastAPI skeleton
    ↓
Domain rules
    ↓
Database foundation
    ↓
SQL repository
    ↓
Service workflows
    ↓
HTTP contract and routes
    ↓
Transactions and error translation
    ↓
Manual end-to-end demo
    ↓
Two lean integration tests
    ↓
Alembic migration
    ↓
README and trade-off discussion
```

### Status key

| Label | Meaning |
|---|---|
| **Create** | Add the file for the first time. |
| **Modify** | Return to an existing file because a new layer now needs wiring. |
| **Generate** | A tool creates the initial file or directory. |
| **Defer** | Valuable, but safe to postpone until the core workflow works. |

---

# 2. Requirement-to-architecture translation

Before touching code, convert the requirements into responsibilities.

Assume the interviewer asks for these capabilities:

```text
Create a short URL
Use an optional custom alias
Redirect by short code
Retrieve URL metadata
List URLs
Delete a URL
Support optional expiration
Track redirect count
Persist data across restarts
Return useful HTTP errors
```

Translate them into layers:

| Requirement | Owning layer/file area |
|---|---|
| Validate request payloads | `schemas.py`, `api_types.py` |
| Represent a shortened URL | `models.py` |
| Check expiration | `models.py` / `service.py` |
| Generate or reserve aliases | `service.py`, `constants.py` |
| Store and retrieve data | `sql_repository.py` |
| Describe database table | `database_models.py` |
| Manage sessions and engine | `database.py`, `dependencies.py` |
| Convert ORM ↔ domain | `persistence_mappers.py` |
| Coordinate use cases | `service.py` |
| Expose HTTP endpoints | `routers/urls.py`, `routers/redirects.py` |
| Convert expected failures to HTTP | `exceptions.py`, `exception_handlers.py` |
| Manage schema versions | `migrations/`, `alembic.ini` |
| Verify V3-specific risks | `tests/integration/test_database_integration.py` |

## First whiteboard sketch

```text
Client
  ↓
FastAPI route
  ↓
Pydantic schema
  ↓
ShortUrlService
  ↓
ShortUrlRepositoryProtocol
  ↓
SQLShortUrlRepository
  ↓
SQLAlchemy Session
  ↓
SQLite
```

Keep this dependency direction throughout the implementation.

---

# 3. Three-hour interview time box

This is a guide, not a rigid timer.

| Approx. time | Focus | Exit condition |
|---:|---|---|
| 0–15 min | Clarify requirements and API contract | Endpoints and assumptions are written down. |
| 15–30 min | Project setup and health endpoint | Application starts and `/health` returns `200`. |
| 30–60 min | Domain, exceptions, configuration, database model | Core types and table shape are defined. |
| 60–105 min | SQL repository and service | Create/get/delete/list work from Python. |
| 105–145 min | Dependencies, schemas, routes, handlers | End-to-end API works. |
| 145–165 min | Manual verification and fixes | Create → redirect → retrieve → delete works. |
| 165–180 min | Two lean tests or migration/documentation | Highest-risk gaps are covered. |

When time becomes tight, prioritise:

```text
Working vertical path
    > correct transaction boundary
    > clear design explanation
    > two focused tests
    > optional documentation polish
```

---

# 4. End-to-end file-creation sequence

## Step 0 — Write the contract before files

No application file yet.

Write the intended endpoints in notes or at the top of the README:

```text
GET    /health
POST   /urls
GET    /urls
GET    /urls/{short_code}
DELETE /urls/{short_code}
GET    /{short_code}
```

Choose the major response semantics:

```text
201  URL created
204  URL deleted
307  Temporary redirect
400  Invalid business input
404  Short code missing
409  Alias already exists
410  URL expired
422  Request validation failed
500  Unexpected failure
```

Clarify assumptions aloud:

- Short codes are case-sensitive or case-insensitive.
- Redirects use `307` rather than `301`.
- Expired links remain stored but cannot redirect.
- Redirect count increments only for successful active redirects.
- SQLite is selected for a self-contained interview implementation.
- The database unique constraint is the final alias-authority.

### Exit condition

You know what must work before designing internal abstractions.

---

## Step 1 — Create project metadata and package skeleton

### Create

```text
pyproject.toml
.gitignore
.env.example
README.md                 # initially a small placeholder
app/__init__.py
app/routers/__init__.py
```

### `pyproject.toml`

Add the minimum dependencies:

```text
fastapi[standard]
pydantic-settings
sqlalchemy
```

Development dependencies:

```text
pytest
httpx
alembic
ruff                    # optional but useful
```

### `.gitignore`

Ignore:

```text
.env
*.db
*.db-shm
*.db-wal
__pycache__/
.pytest_cache/
.ruff_cache/
*.egg-info/
```

### `.env.example`

Start with:

```text
TINYURL_APP_NAME
TINYURL_APP_VERSION
TINYURL_PUBLIC_BASE_URL
TINYURL_DATABASE_URL
TINYURL_DATABASE_ECHO
TINYURL_LOG_LEVEL
```

### Why this is first

It establishes a runnable Python package and makes environmental assumptions explicit.

### Mental link

```text
Project metadata
    ↓
Importable application package
    ↓
Files can now depend on one another predictably
```

---

## Step 2 — Create typed configuration

### Create

```text
app/config.py
```

### Owns

```text
Settings
get_settings()
```

Recommended settings:

```text
app_name
app_version
public_base_url
database_url
database_echo
log_level
```

Use `pydantic-settings` and cache the settings object.

### Why now

The database engine and FastAPI application both need configuration. Creating configuration before those modules prevents hard-coded values from spreading.

### Dependency direction

```text
config.py
   ↑       ↑
database  main/dependencies
```

No other low-level module should import settings from `main.py` or `dependencies.py`.

---

## Step 3 — Create the database foundation

### Create

```text
app/database.py
```

### Owns

```text
engine
SessionFactory
check_database_connection()
dispose_database()
```

### Important choices

```text
One Engine per process
One session factory per process
No global Session object
No commit hidden in this module
```

Default database URL:

```text
sqlite:///./tinyurl.db
```

Session factory configuration:

```text
autoflush=False
expire_on_commit=False
```

### Why before the ORM model

The ORM model describes the schema, while `database.py` owns connectivity and session creation. They are adjacent concerns but should remain separate.

### Exit condition

A simple `SELECT 1` connection check succeeds.

---

## Step 4 — Create a minimal runnable FastAPI application

### Create

```text
app/main.py
```

At this stage, keep it intentionally small:

```text
Create FastAPI instance
Add application lifespan
Check database connectivity at startup
Dispose engine at shutdown
Expose GET /health
```

Do **not** wait until all routes exist before proving the app boots.

### Run

```bash
uvicorn app.main:app --reload
```

Verify:

```text
GET /health → 200
```

### Why create `main.py` early

You now have a continuously runnable shell. Every later layer can be integrated incrementally instead of debugging the entire project at once.

### Later modifications

`main.py` will later register:

```text
logging
exception handlers
URL router
redirect router
```

---

## Step 5 — Create shared business constants

### Create

```text
app/constants.py
```

### Owns

```text
SHORT_CODE_MIN_LENGTH
SHORT_CODE_MAX_LENGTH
SHORT_CODE_PATTERN
RESERVED_SHORT_CODES
```

Example reserved paths:

```text
health
urls
docs
redoc
openapi.json
```

### Why this is a neutral module

Both the HTTP schemas and database model need short-code information. Neither layer should import those rules from the other.

```text
constants.py
   ↑              ↑
schemas.py   database_models.py
```

---

## Step 6 — Create the domain model

### Create

```text
app/models.py
```

### Main type

```text
ShortUrl
├── short_code
├── destination_url
├── created_at
├── expires_at
└── redirect_count
```

### Behaviour

```text
is_expired(current_time)
record_redirect()
remaining_seconds(current_time)
```

### Important rule

The domain model should import neither FastAPI nor SQLAlchemy.

### Why it appears before service and repository

The application must first define what a short URL **is** before defining how it is stored or exposed.

---

## Step 7 — Create the exception vocabulary

### Create

```text
app/exceptions.py
```

### Suggested hierarchy

```text
TinyUrlError
├── DuplicateShortCodeError
├── ReservedShortCodeError
├── ShortCodeNotFoundError
├── ShortUrlExpiredError
├── InvalidExpirationError
└── ShortCodeGenerationError
```

### Why now

The repository and service need stable expected-failure types. The HTTP layer will later translate these exceptions without knowing storage details.

### Mental link

```text
Database/service failure
    ↓ named application exception
HTTP adapter
    ↓ status code + public error response
```

---

## Step 8 — Define the repository contract

### Create

```text
app/repository_protocol.py
```

### Contract

```text
save(short_url)
get(short_code)
exists(short_code)
list_all()
delete(short_code)
increment_redirect_count(short_code)
```

Use a Python `Protocol`.

### Why before the concrete repository

The service should depend on required behaviour, not SQLAlchemy itself.

```text
ShortUrlService
        ↓
ShortUrlRepositoryProtocol
        ↑
SQLShortUrlRepository
```

### Interview explanation

> “The protocol is the application-facing storage contract. SQLAlchemy is one adapter implementing it.”

---

## Step 9 — Define the SQLAlchemy persistence model

### Create

```text
app/database_models.py
```

### Owns

```text
Base(DeclarativeBase)
ShortUrlRecord
```

### Table

```text
short_urls
├── id                  INTEGER PRIMARY KEY
├── short_code          VARCHAR(...) NOT NULL UNIQUE
├── destination_url     TEXT NOT NULL
├── created_at          DATETIME NOT NULL
├── expires_at          DATETIME NULL
└── redirect_count      INTEGER NOT NULL DEFAULT 0
```

### Constraints

```text
uq_short_urls_short_code
ck_short_urls_redirect_count_non_negative
```

### Key design decision

```text
ShortUrl          = domain model
ShortUrlRecord    = persistence model
```

The internal database `id` does not need to enter the domain or API response.

### Why this file is separate from `database.py`

```text
database.py
    Connectivity and sessions

database_models.py
    Schema and ORM mapping
```

---

## Step 10 — Create domain/persistence mapping

### Create

```text
app/persistence_mappers.py
```

### Owns

```text
to_short_url_record(short_url)
to_short_url_domain(record)
normalise_to_utc(datetime)
```

### Flow

```text
ShortUrl
   ↓ to_short_url_record
ShortUrlRecord
   ↓ database
ShortUrlRecord
   ↓ to_short_url_domain
ShortUrl
```

### Why not return ORM records to the service

It prevents SQLAlchemy state and database-only fields from leaking into business logic.

### SQLite timestamp note

SQLite may return naive timestamps. The mapper restores the application rule that domain timestamps are UTC-aware.

---

## Step 11 — Implement the SQL repository

### Create

```text
app/sql_repository.py
```

### Owns

```text
SQLShortUrlRepository
├── save()
├── get()
├── exists()
├── list_all()
├── delete()
└── increment_redirect_count()
```

### Constructor

The repository receives a `Session`:

```text
SQLShortUrlRepository(session)
```

It must not create or close its own request session.

### Write rule

```text
Repository flushes
Dependency commits or rolls back
```

### Duplicate handling

```text
INSERT
    ↓
Database unique violation
    ↓
SQLAlchemy IntegrityError
    ↓
DuplicateShortCodeError
```

Translate only the short-code uniqueness failure, not every integrity error.

### Generated-code collision retries

Use a nested transaction/savepoint around an insertion attempt:

```text
Outer request transaction
    ↓
SAVEPOINT
    ↓
Attempt INSERT
    ↓ duplicate
Rollback to SAVEPOINT
    ↓
Outer transaction remains usable
```

### Redirect count

Use an atomic statement:

```text
redirect_count = redirect_count + 1
```

Avoid a Python read-modify-write sequence.

### Manual verification before HTTP

Open Session A, save and commit. Open Session B and retrieve the same record.

This isolates persistence debugging from route debugging.

---

## Step 12 — Implement business workflows

### Create

```text
app/service.py
```

### Owns

```text
ShortUrlService
├── create_url()
├── resolve_url()
├── get_url_details()
├── list_urls()
└── delete_url()
```

### Dependencies injected into the constructor

```text
repository
code_generator
clock
max_generation_attempts
reserved_short_codes
```

### `create_url()` flow

```text
Validate expiration
    ↓
Use custom alias or generate one
    ↓
Reject reserved aliases
    ↓
Create ShortUrl domain object
    ↓
repository.save()
    ↓
On generated collision: retry
On custom collision: raise conflict
```

### `resolve_url()` flow

```text
repository.get()
    ↓
Missing? → ShortCodeNotFoundError
    ↓
Expired? → ShortUrlExpiredError
    ↓
repository.increment_redirect_count()
    ↓
Return active domain object
```

### Important boundary

The service does not know:

```text
FastAPI
HTTP status codes
SQLAlchemy Session
SQLite
JSON
```

---

## Step 13 — Define HTTP request and response schemas

### Create

```text
app/schemas.py
```

### Suggested schemas

```text
CreateShortUrlRequest
ShortUrlResponse
ShortUrlListResponse           # optional wrapper
HealthResponse
ErrorDetail
ErrorResponse
```

### Validate at the boundary

```text
destination_url       valid HTTP/HTTPS URL
custom_code           allowed pattern and length
expires_in_seconds    positive when supplied
```

### Do not duplicate service responsibilities

Pydantic validates input shape. The service still owns business rules such as reserved aliases and generated-code retry behaviour.

---

## Step 14 — Create reusable HTTP parameter types

### Create

```text
app/api_types.py
```

### Owns

Reusable `Annotated` path/query definitions such as:

```text
ShortCodePath
LimitQuery              # only if pagination is implemented
OffsetQuery             # only if pagination is implemented
```

### Why separate this from schemas

`schemas.py` defines request/response bodies. `api_types.py` defines reusable HTTP parameters.

### Interview simplification

When time is tight, these types can temporarily remain in the router and be extracted later. The final clean project uses this file.

---

## Step 15 — Create HTTP response mapping

### Create

```text
app/mappers.py
```

### Owns

```text
to_short_url_response(short_url, public_base_url)
```

### Why mapping exists

The response contains values that are not database fields:

```text
short_url = public_base_url + short_code
```

Keep URL construction and response-model assembly out of the domain and repository.

### Boundary map

```text
ShortUrlRecord
    ↓ persistence_mappers.py
ShortUrl
    ↓ mappers.py
ShortUrlResponse
```

---

## Step 16 — Create request-scoped dependencies

### Create

```text
app/dependencies.py
```

### Owns

```text
SettingsDependency
get_database_session()
DatabaseSessionDependency
get_short_url_service()
ShortUrlServiceDependency
```

### Session lifecycle

```text
Request begins
    ↓
Create Session
    ↓
Yield Session
    ↓
Route/service/repository work
    ↓
Success → commit
Failure → rollback
    ↓
Close Session
```

Use function-scoped yield cleanup so commit completes before the success response is transmitted.

### Per-request graph

```text
Request
├── Session
├── SQLShortUrlRepository(Session)
└── ShortUrlService(repository)
```

### Critical rule

Never create one global SQLAlchemy session for all requests.

---

## Step 17 — Create the URL-management router

### Create

```text
app/routers/urls.py
```

### Endpoints

```text
POST   /urls
GET    /urls
GET    /urls/{short_code}
DELETE /urls/{short_code}
```

### Router responsibilities

```text
Receive validated HTTP input
Call one service use case
Map domain result to response schema
Set HTTP status and headers
```

### Router should not

```text
Write SQL
Create sessions
Check database constraints
Generate aliases directly
Build ORM objects
Commit transactions
```

### First vertical slice recommendation

Implement in this order:

```text
POST /urls
    ↓
GET /urls/{short_code}
    ↓
DELETE /urls/{short_code}
    ↓
GET /urls
```

Create and retrieve first; listing is less important than the primary workflow.

---

## Step 18 — Create the public redirect router

### Create

```text
app/routers/redirects.py
```

### Endpoint

```text
GET /{short_code}
```

### Flow

```text
Path alias
    ↓
service.resolve_url()
    ↓
RedirectResponse(status_code=307)
```

Add a defensive header:

```text
Cache-Control: no-store
```

### Route-order warning

The catch-all redirect route must be registered after specific routers such as `/health` and `/urls`, otherwise it can capture their first path segment.

---

## Step 19 — Create the public error documentation/constants

### Create

```text
app/api_docs.py
```

### Owns

Reusable OpenAPI response descriptions and examples.

Possible content:

```text
NOT_FOUND_RESPONSE
CONFLICT_RESPONSE
EXPIRED_RESPONSE
VALIDATION_RESPONSE
INTERNAL_ERROR_RESPONSE
```

### Why this is created after routes work

It improves consistency and generated documentation but should not block the primary application flow.

### Time-pressure rule

This is a polish file. Defer it until the API works.

---

## Step 20 — Create global exception translation

### Create

```text
app/exception_handlers.py
```

### Owns

```text
register_exception_handlers(app)
```

Map expected failures:

| Application failure | HTTP |
|---|---:|
| Invalid expiration | 400 |
| Missing short code | 404 |
| Duplicate/reserved alias | 409 |
| Expired URL | 410 |
| Code generation exhausted | 503 |
| Pydantic validation | 422 |
| Unknown exception | 500 |

### Boundary guarantee

```text
SQLAlchemy IntegrityError
    ✗ should not be exposed publicly

DuplicateShortCodeError
    ↓
HTTP 409 with stable error body
```

### Safe `500`

Log the real exception internally, but return a generic public message.

---

## Step 21 — Add logging configuration

### Create

```text
app/logging_config.py
```

### Owns

```text
configure_logging(log_level)
```

### Useful logs

```text
application_started
application_stopped
short_url_created
short_url_resolved
short_url_deleted
unexpected_error
```

### Avoid logging

```text
full destination URLs when not necessary
credentials
raw database URLs containing passwords
request bodies by default
```

### Time-pressure rule

Start with standard library logging. Do not spend interview time building a logging framework.

---

## Step 22 — Complete application composition

### Modify

```text
app/main.py
```

### Final responsibilities

```text
Load settings
Configure logging
Create FastAPI application
Define lifespan
Check database connectivity
Register exception handlers
Register URL router
Register redirect router last
Expose health endpoint
```

### Final registration order

```text
1. /health
2. /urls routes
3. /{short_code} catch-all redirect
```

### Important schema rule

Once Alembic is introduced, `main.py` should not call `Base.metadata.create_all()`.

---

# 5. First complete end-to-end manual verification

Before writing tests, prove the system manually.

## 1. Create the schema temporarily

Before Alembic exists, using `Base.metadata.create_all()` in a one-off command is acceptable:

```text
Python command
    ↓
Base.metadata.create_all(engine)
```

Do not hide this permanently in application startup.

## 2. Start the API

```bash
uvicorn app.main:app --reload
```

## 3. Create

```text
POST /urls
custom_code = article
    ↓
201 Created
```

## 4. Retrieve

```text
GET /urls/article
    ↓
redirect_count = 0
```

## 5. Redirect

```text
GET /article
    ↓
307 Location: destination
```

## 6. Retrieve again

```text
GET /urls/article
    ↓
redirect_count = 1
```

## 7. Restart

Stop and restart Uvicorn.

```text
GET /urls/article
    ↓
record still exists
```

## 8. Duplicate

```text
POST /urls with custom_code = article
    ↓
409 Conflict
```

## 9. Delete

```text
DELETE /urls/article
    ↓
204
```

## 10. Retrieve deleted alias

```text
GET /urls/article
    ↓
404
```

### Exit condition

The primary workflow is complete before adding migration tooling or broad test infrastructure.

---

# 6. Add only two high-value integration tests

## Create

```text
tests/integration/test_database_integration.py
```

This is the only mandatory V3 test file for the interview-focused implementation.

## Test fixture

Create a temporary SQLite database using pytest `tmp_path`.

```text
Each test
    ↓
Unique temporary .db file
    ↓
Create schema
    ↓
Run real SQLAlchemy repository/API
    ↓
Dispose engine
```

## Test 1 — Persistence and redirect-count durability

```text
Session 1
    Create and commit URL
    ↓
Session 2
    Resolve and commit count increment
    ↓
Session 3
    Verify URL exists and count = 1
```

Covers:

```text
Domain → ORM mapping
Repository insertion
Commit
Persistence across sessions
Atomic count update
ORM → domain mapping
```

## Test 2 — Database uniqueness becomes HTTP 409

```text
First POST with alias
    ↓ 201
Second POST with same alias
    ↓ database UNIQUE failure
    ↓ repository translation
    ↓ application exception
    ↓ HTTP 409
```

Use a dependency override for `get_database_session` so the real service and SQL repository operate against the temporary database.

## Deliberately not added

```text
A test per repository method
A test per schema field
Large factory hierarchy
Migration test
Concurrency/load suite
Multiple database backends
```

### Interview statement

> “I kept the tests targeted to the new persistence risks: data durability and database-enforced uniqueness. The rest can be expanded after the core exercise.”

---

# 7. Introduce Alembic after the application works

## Modify

```text
pyproject.toml
```

Ensure Alembic is in the development dependencies.

## Generate

```text
alembic.ini
migrations/README
migrations/env.py
migrations/script.py.mako
migrations/versions/
```

Command:

```bash
alembic init migrations
```

## Modify `migrations/env.py`

Connect Alembic to:

```text
Settings.database_url
Base.metadata
```

Recommended options:

```text
compare_type=True
render_as_batch=True for SQLite
NullPool for migration process
```

## Generate the first migration

```bash
alembic revision --autogenerate -m "create short urls table"
```

## Review the generated file

### Generate/create

```text
migrations/versions/<revision>_create_short_urls_table.py
```

Confirm `upgrade()` creates:

```text
short_urls table
primary key
unique short_code constraint
non-negative redirect-count check
all required columns
```

Confirm `downgrade()` drops the table.

## Apply

```bash
alembic upgrade head
```

## Remove runtime schema creation

### Modify

```text
app/main.py
app/database.py                 # if create_database_tables() was temporarily added
```

Alembic now owns schema creation and evolution.

### Deployment/run order

```text
alembic upgrade head
    ↓
uvicorn app.main:app
```

### Important interview explanation

> “Autogenerate gives me a candidate migration. I inspect the upgrade and downgrade operations before applying it.”

---

# 8. Finish documentation and project packaging

## Modify

```text
README.md
.env.example
```

## README should include

```text
Problem summary
Architecture diagram
Setup command
Environment variables
Migration command
Run command
Endpoint examples
Two-test command
Design decisions
Known limitations
Production extensions
```

## Useful commands

```text
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
python -m pytest tests/integration/test_database_integration.py -q
```

## Known limitations to state honestly

```text
SQLite instead of production PostgreSQL
No authentication/ownership
No pagination unless explicitly added
No rate limiting
No malware/phishing screening
Redirect row can become a write hotspot
Expiration check and increment are separate operations
No migration smoke test
Only lean persistence-focused testing
```

---

# 9. Complete chronological file list

This is the condensed order to memorise.

| Order | Action | File(s) | Capability unlocked |
|---:|---|---|---|
| 0 | Notes | Requirements/API contract | Clear target and assumptions |
| 1 | Create | `pyproject.toml`, `.gitignore`, `.env.example`, `README.md` | Installable project and environment contract |
| 2 | Create | `app/__init__.py`, `app/routers/__init__.py` | Importable package structure |
| 3 | Create | `app/config.py` | Typed application/database settings |
| 4 | Create | `app/database.py` | Engine, session factory, connectivity |
| 5 | Create | `app/main.py` | Runnable FastAPI app and `/health` |
| 6 | Create | `app/constants.py` | Shared alias invariants and reserved routes |
| 7 | Create | `app/models.py` | Framework-independent `ShortUrl` domain model |
| 8 | Create | `app/exceptions.py` | Stable expected-failure vocabulary |
| 9 | Create | `app/repository_protocol.py` | Storage contract for service |
| 10 | Create | `app/database_models.py` | ORM table and database constraints |
| 11 | Create | `app/persistence_mappers.py` | Domain ↔ ORM conversion |
| 12 | Create | `app/sql_repository.py` | Persistent CRUD, uniqueness translation, atomic count |
| 13 | Create | `app/service.py` | Create/resolve/details/list/delete use cases |
| 14 | Create | `app/schemas.py` | Request/response validation contract |
| 15 | Create | `app/api_types.py` | Reusable path/query parameter definitions |
| 16 | Create | `app/mappers.py` | Domain → HTTP response conversion |
| 17 | Create | `app/dependencies.py` | Per-request session, repository, service, transaction |
| 18 | Create | `app/routers/urls.py` | URL-management endpoints |
| 19 | Create | `app/routers/redirects.py` | Public redirect endpoint |
| 20 | Create/Defer | `app/api_docs.py` | Reusable OpenAPI error documentation |
| 21 | Create | `app/exception_handlers.py` | Application failures → consistent HTTP errors |
| 22 | Create/Defer | `app/logging_config.py` | Central logging setup |
| 23 | Modify | `app/main.py` | Complete router/handler/logging composition |
| 24 | Create | `tests/integration/test_database_integration.py` | Two V3 risk-focused tests |
| 25 | Generate | `alembic.ini`, `migrations/*` | Versioned schema management |
| 26 | Generate/Review | Initial migration revision | Reproducible `short_urls` schema |
| 27 | Modify | `app/main.py`, `app/database.py` | Alembic becomes sole schema owner |
| 28 | Modify | `README.md`, `.env.example` | Reproducible setup and interview handoff |

---

# 10. Final project tree

```text
tiny_url/
├── app/
│   ├── __init__.py
│   ├── api_docs.py
│   ├── api_types.py
│   ├── config.py
│   ├── constants.py
│   ├── database.py
│   ├── database_models.py
│   ├── dependencies.py
│   ├── exception_handlers.py
│   ├── exceptions.py
│   ├── logging_config.py
│   ├── main.py
│   ├── mappers.py
│   ├── models.py
│   ├── persistence_mappers.py
│   ├── repository_protocol.py
│   ├── schemas.py
│   ├── service.py
│   ├── sql_repository.py
│   └── routers/
│       ├── __init__.py
│       ├── redirects.py
│       └── urls.py
├── migrations/
│   ├── README
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── <revision>_create_short_urls_table.py
├── tests/
│   └── integration/
│       └── test_database_integration.py
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
└── README.md
```

### Optional files not required for the V3 interview implementation

```text
app/repository.py             # in-memory repository, useful for earlier learning but not required here
app/cli.py
app/__main__.py
large V1/V2 unit and API test suite
```

The interview build goes directly to the SQL repository.

---

# 11. Final dependency map

```text
app/main.py
├── app/config.py
├── app/database.py
├── app/logging_config.py
├── app/exception_handlers.py
└── app/routers/
    ├── urls.py
    └── redirects.py

app/routers/*.py
├── app/dependencies.py
├── app/schemas.py
├── app/api_types.py
└── app/mappers.py

app/dependencies.py
├── app/config.py
├── app/database.py
├── app/sql_repository.py
└── app/service.py

app/service.py
├── app/models.py
├── app/exceptions.py
├── app/constants.py
└── app/repository_protocol.py

app/sql_repository.py
├── app/database_models.py
├── app/persistence_mappers.py
├── app/models.py
└── app/exceptions.py

app/database_models.py
└── app/constants.py

app/persistence_mappers.py
├── app/database_models.py
└── app/models.py

migrations/env.py
├── app/config.py
└── app/database_models.py → Base.metadata
```

### Dependency rule to remember

```text
HTTP layer
    ↓
Application/service layer
    ↓
Repository contract
    ↓
Persistence adapter
    ↓
Database
```

Low-level modules must not import routers or FastAPI schemas.

---

# 12. Vertical-slice checkpoint map

Use these checkpoints to avoid building too much before running anything.

## Checkpoint A — Application shell

Files:

```text
config.py
database.py
main.py
```

Proof:

```text
GET /health → 200
Database SELECT 1 succeeds
```

## Checkpoint B — Persistence works from Python

Files added:

```text
constants.py
models.py
exceptions.py
repository_protocol.py
database_models.py
persistence_mappers.py
sql_repository.py
service.py
```

Proof:

```text
Session A creates
Session B retrieves
Duplicate alias becomes DuplicateShortCodeError
```

## Checkpoint C — Primary HTTP path works

Files added:

```text
schemas.py
api_types.py
mappers.py
dependencies.py
routers/urls.py
exception_handlers.py
```

Proof:

```text
POST /urls → 201
GET /urls/{code} → 200
Duplicate → 409
```

## Checkpoint D — Redirect path works

File added:

```text
routers/redirects.py
```

Proof:

```text
GET /{code} → 307
Redirect count becomes 1
Expired URL → 410
```

## Checkpoint E — Interview-complete persistence story

Files added/generated:

```text
tests/integration/test_database_integration.py
alembic.ini
migrations/*
README.md updates
```

Proof:

```text
2 integration tests pass
alembic upgrade head works from blank database
Application starts without create_all()
```

---

# 13. Time-pressure fallback map

When fewer than three hours remain, simplify deliberately rather than creating half-finished layers.

## Must keep

```text
config.py
database.py
models.py
exceptions.py
database_models.py
sql_repository.py
service.py
dependencies.py
schemas.py
routers/urls.py
routers/redirects.py
main.py
```

## Can merge temporarily

```text
api_types.py → routers or schemas.py
mappers.py → routers/urls.py
api_docs.py → inline response definitions
logging_config.py → basic logging in main.py
persistence_mappers.py → private functions in sql_repository.py
repository_protocol.py → direct repository typing, then explain extraction
```

## Can defer until core works

```text
GET /urls listing
Extensive OpenAPI examples
Alembic downgrade polish
README screenshots
Additional tests
Pagination
Authentication
Docker
```

## Do not sacrifice

```text
Database UNIQUE constraint
One Session per request
Commit/rollback handling
Clear expected error responses
Working create + redirect flow
Honest trade-off explanation
```

---

# 14. Interview explanation tied to file order

When the interviewer asks why you built it this way:

> “I first clarified the API and got a minimal FastAPI application running. Then I established the framework-independent domain model and error vocabulary. I created the database engine and ORM schema, followed by explicit domain-to-persistence mapping and a session-injected SQL repository. The service depends on a repository protocol, so it coordinates business workflows without knowing SQLAlchemy. FastAPI dependencies create one session and transaction per request, while routes remain thin HTTP adapters. I added two focused integration tests for persistence and database uniqueness, then introduced Alembic so schema creation is versioned rather than hidden in application startup.”

---

# 15. One-line memory sequence

```text
Requirements
→ Project
→ Config
→ Database
→ Health app
→ Constants
→ Domain
→ Exceptions
→ Repository contract
→ ORM model
→ Persistence mapper
→ SQL repository
→ Service
→ Schemas
→ API types
→ Response mapper
→ Dependencies
→ URL routes
→ Redirect route
→ Exception handlers
→ Logging/docs
→ Final app wiring
→ Manual demo
→ Two integration tests
→ Alembic
→ README
```

This is the complete **direct-to-V3 interview build map**.
