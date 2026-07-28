# TinyURL V3 Architecture

Explore how one short URL is represented across the HTTP, domain, persistence,
and database layers.

## Quick navigation

- [Persistence model](#sqlalchemy-persistence-model)
- [Three-model mental map](#the-three-model-mental-map)
- [Representation responsibilities](#representation-responsibilities)
- [Final request flow](#final-request-flow)
- [Final V3 file map](#final-v3-file-map)
- [Request lifecycle](#request-lifecycle)

---

## SQLAlchemy persistence model

| Layer | Representation |
| --- | --- |
| Existing domain model | `ShortUrl` |
| New persistence model | `ShortUrlRecord` |
| Database table | `short_urls` |

## The three-model mental map

After this module, TinyURL has three different representations of the same
underlying concept:

```text
HTTP request/response
        ↓
Pydantic schemas
CreateShortUrlRequest
ShortUrlResponse
        ↓
Domain layer
ShortUrl
        ↓
Persistence layer
ShortUrlRecord
        ↓
Database
short_urls table
```

## Representation responsibilities

| Representation | Purpose |
| --- | --- |
| `CreateShortUrlRequest` | Validate incoming HTTP data |
| `ShortUrlResponse` | Control outgoing API data |
| `ShortUrl` | Represent domain state and behaviour |
| `ShortUrlRecord` | Map Python attributes to database columns |
| `short_urls` | Persist data in the relational database |

## Final request flow

<details open>
<summary><strong>Expand the complete request lifecycle</strong></summary>

```text
HTTP request
    ↓
FastAPI dependency
    ↓
New SQLAlchemy Session
    ↓
SQLShortUrlRepository
    ↓
ShortUrlService
    ↓
SQLite
    ↓
Commit or rollback
    ↓
Close Session
```

</details>

## Final V3 file map

### Application core

```text
app/
├── models.py
├── exceptions.py
├── service.py
├── repository_protocol.py
└── constants.py
```

#### Responsibilities

| File | Responsibility |
| --- | --- |
| `models.py` | Domain state and object-specific behaviour |
| `exceptions.py` | Application and domain failures |
| `service.py` | Business workflows |
| `repository_protocol.py` | Storage contract required by the service |
| `constants.py` | Shared short-code rules and reserved names |

### Persistence layer

```text
app/
├── database.py
├── database_models.py
├── persistence_mappers.py
└── sql_repository.py
```

| File | Responsibility |
| --- | --- |
| `database.py` | Engine and session factory |
| `database_models.py` | SQLAlchemy ORM table mappings |
| `persistence_mappers.py` | Domain ↔ ORM conversions |
| `sql_repository.py` | Database-backed repository operations |

### HTTP layer

```text
app/
├── schemas.py
├── api_types.py
├── api_docs.py
├── mappers.py
├── exception_handlers.py
├── dependencies.py
├── main.py
└── routers/
    ├── urls.py
    └── redirects.py
```

### Database migrations

```text
migrations/
├── env.py
├── script.py.mako
└── versions/
    └── <revision>_create_short_urls_table.py
```

### Lean V3 tests

```text
tests/integration/
└── test_database_integration.py
```

Only two database-focused integration tests:

1. Persistence and redirect-count durability.
2. Unique constraint translated into HTTP `409 Conflict`.

## Request lifecycle

<details open>
<summary><strong>Create URL — POST /urls</strong></summary>

```text
POST /urls
    ↓
CreateShortUrlRequest validates input
    ↓
FastAPI creates one database session
    ↓
SQLShortUrlRepository created with session
    ↓
ShortUrlService.create_url()
    ↓
Domain ShortUrl created
    ↓
Mapped to ShortUrlRecord
    ↓
INSERT + flush
    ↓
Database uniqueness constraint checked
    ↓
Route returns ShortUrlResponse
    ↓
Session commits
    ↓
HTTP 201 sent
```

</details>

<details>
<summary><strong>Duplicate custom alias</strong></summary>

```text
POST /urls with existing short_code
    ↓
Database UNIQUE constraint fails
    ↓
SQLAlchemy IntegrityError
    ↓
SQL repository recognises short-code conflict
    ↓
DuplicateShortCodeError
    ↓
Global exception handler
    ↓
HTTP 409
    ↓
Request transaction rolls back
```

</details>

<details>
<summary><strong>Redirect — GET /python</strong></summary>

```text
GET /python
    ↓
Retrieve URL
    ↓
Missing?
    → 404

Expired?
    → 410

Active?
    ↓
UPDATE redirect_count =
    redirect_count + 1
    ↓
Commit transaction
    ↓
307 with Location header
```

</details>
