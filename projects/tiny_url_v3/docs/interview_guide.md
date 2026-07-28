# TinyURL V3 Interview Guide

A practical demo sequence, concise project explanation, architecture
walkthrough, likely interview questions, and an honest review of current
limitations.

## Quick navigation

- [Recommended demo sequence](#recommended-interview-demo-sequence)
- [One-minute explanation](#one-minute-interview-explanation)
- [Five-minute architecture walkthrough](#five-minute-architecture-walkthrough)
- [Likely interview questions](#likely-interview-questions)
- [Current limitations](#current-limitations)

---

## Recommended interview demo sequence

> Do not begin by explaining every file. Show the working behaviour first.

### Step 1: Start from a clean database

```bash
rm -f tinyurl.db
alembic upgrade head
uvicorn app.main:app --reload
```

Explain:

> “Alembic creates the versioned schema before the application starts.”

### Step 2: Create a link

```bash
curl -i \
  -X POST \
  http://127.0.0.1:8000/urls \
  -H "Content-Type: application/json" \
  -d '{
    "destination_url": "https://example.com/article",
    "custom_code": "article"
  }'
```

Highlight:

```http
201 Created
Location: /urls/article
```

### Step 3: Retrieve metadata

```bash
curl http://127.0.0.1:8000/urls/article
```

Highlight:

```json
{
  "short_code": "article",
  "redirect_count": 0
}
```

### Step 4: Redirect

```bash
curl -i http://127.0.0.1:8000/article
```

Highlight:

```http
307 Temporary Redirect
Location: https://example.com/article
```

### Step 5: Show the persistent count

```bash
curl http://127.0.0.1:8000/urls/article
```

Highlight:

```json
{
  "redirect_count": 1
}
```

### Step 6: Restart the server

Restart Uvicorn and retrieve the same URL.

Explain:

> “This demonstrates the difference from V2: the data and redirect count
> survive the process restart.”

### Step 7: Demonstrate database uniqueness

Submit another URL using the same alias.

Highlight:

```http
409 Conflict
```

Explain the full exception translation.

---

## One-minute interview explanation

> “I built TinyURL in three stages. V1 established a framework-independent
> domain model, service layer, repository contract, injected clock and code
> generator, and CLI. V2 exposed the same core through FastAPI with Pydantic
> validation, dependency injection, response mapping, redirects, and central
> error handling. V3 replaced the in-memory repository with SQLAlchemy while
> keeping the HTTP contract and most service logic unchanged. Each request
> receives its own session and transaction. The SQL repository maps between
> domain and ORM models, flushes without owning the outer commit, translates
> unique constraint failures, and uses an atomic database update for redirect
> counts. Alembic owns schema migrations. Testing is intentionally lean and
> covers the two main new risks: persistence across sessions and
> database-enforced uniqueness returning the expected API conflict.”

---

## Five-minute architecture walkthrough

Use this order:

### 1. Start with the domain

- `ShortUrl`
- `ShortUrlService`
- `ShortUrlRepositoryProtocol`

Explain that the core does not know FastAPI or SQLAlchemy.

### 2. Explain the persistence adapter

- `ShortUrlRecord`
- Persistence mapper
- `SQLShortUrlRepository`

Explain the internal `id` versus public `short_code`.

### 3. Explain the transaction boundary

```text
FastAPI dependency
    → Session
    → Repository
    → Service
    → Commit/rollback
```

### 4. Explain database integrity

```sql
UNIQUE(short_code)
CHECK(redirect_count >= 0)
```

### 5. Explain concurrency-sensitive behaviour

- Savepoint for generated collision retries.
- Atomic SQL increment for redirect counts.

### 6. Explain migrations

```text
Base.metadata
    ↓ autogenerate
Alembic revision
    ↓ review
alembic upgrade head
```

### 7. State current limitations honestly

> Do not pretend the application is production-complete.

---

## Likely interview questions

<details open>
<summary><strong>Why not use the ORM model directly as the domain model?</strong></summary>

The ORM model includes persistence concerns such as the internal primary key and
SQLAlchemy state. The domain model stays storage-independent and owns
application behaviour. For a small CRUD application, combining them could
reduce code, but separation makes the storage replacement and testing story
clearer.

</details>

<details>
<summary><strong>Why use a protocol rather than an abstract base class?</strong></summary>

The repository is a small behavioural contract, and Python protocols support
structural typing. Implementations do not need explicit inheritance. An
abstract base class would also be valid if runtime enforcement or shared
implementation were required.

</details>

<details>
<summary><strong>Why SQLite?</strong></summary>

It removes external infrastructure and keeps the exercise runnable. The
database URL is configurable, so PostgreSQL could replace it without changing
routes or business use cases. I would validate PostgreSQL-specific behaviour
before production.

</details>

<details>
<summary><strong>Why is short_code not the primary key?</strong></summary>

It could be. I used a surrogate integer key to separate internal row identity
from the public business identifier and to make future relationships easier.
For the simplest implementation, using `short_code` as the primary key would be
defensible.

</details>

<details>
<summary><strong>Why no repository-level commit?</strong></summary>

A repository method should not unexpectedly complete the request’s entire
transaction. Keeping commit ownership above the repository allows multiple
operations to participate in one atomic use case.

</details>

<details>
<summary><strong>Why use flush()?</strong></summary>

It forces the pending statement and database constraint checks to occur while
the repository can translate a known integrity failure. The outer transaction
remains uncommitted.

</details>

<details>
<summary><strong>Why use a nested transaction?</strong></summary>

The service retries generated alias collisions. A failed flush otherwise leaves
the session unusable until rollback. A savepoint rolls back only that insertion
attempt while keeping the request transaction active.

</details>

<details>
<summary><strong>Why not check exists() first?</strong></summary>

It can be used for convenience, but it cannot guarantee uniqueness. The
database constraint is necessary because check-then-insert has a race
condition.

</details>

<details>
<summary><strong>Why is redirect count an atomic update?</strong></summary>

Two requests performing Python read-modify-write could overwrite one another.
`redirect_count = redirect_count + 1` lets the database update its current
value in one statement.

</details>

<details>
<summary><strong>Why synchronous SQLAlchemy?</strong></summary>

SQLite and the current repository use synchronous database operations, so
synchronous FastAPI handlers are simple and appropriate. For an async
PostgreSQL driver, I would use `AsyncEngine`, `AsyncSession`, and async routes
consistently.

</details>

<details>
<summary><strong>Why only two V3 tests?</strong></summary>

V2 already covers the HTTP contract. V3 tests focus on the new risk surface:
persistence and database constraint translation. With more time, I would add
rollback, migration, concurrency, and production-database tests.

</details>

<details>
<summary><strong>What if the commit fails after the route returns?</strong></summary>

The database dependency uses function-scoped cleanup, so commit runs before the
response is transmitted. A commit failure can still be handled as an internal
error instead of returning false success.

</details>

---

## Current limitations

<details open>
<summary><strong>SQLite concurrency</strong></summary>

SQLite is suitable for local development and interviews, but it is not the
intended high-write database for a large URL-shortening platform.

</details>

<details>
<summary><strong>Expiration race</strong></summary>

The flow currently performs:

```text
Read
    ↓
Check expiration
    ↓
Increment
```

A link could theoretically be deleted or altered between those steps.

A stronger production implementation could combine conditions into one
database operation.

</details>

<details>
<summary><strong>Analytics scalability</strong></summary>

Updating the main URL row for every redirect may become a write hotspot.

At scale:

```text
Redirect request
    ↓
Return destination quickly
    ↓
Publish analytics event asynchronously
```

</details>

<details>
<summary><strong>No authentication or ownership</strong></summary>

Any client can list, inspect, or delete links.

</details>

<details>
<summary><strong>No pagination</strong></summary>

`GET /urls` returns the entire collection.

</details>

<details>
<summary><strong>No destination abuse protection</strong></summary>

There is no phishing, malware, blocklist, or reputation screening.

</details>

<details>
<summary><strong>No custom domains</strong></summary>

The application supports one configured public base URL.

</details>

<details>
<summary><strong>No rate limiting</strong></summary>

Creation and redirect endpoints are not throttled.

</details>

<details>
<summary><strong>No PostgreSQL verification</strong></summary>

The configuration is portable in principle, but database-specific behaviour
must be tested against the actual production database.

</details>

<details>
<summary><strong>No migration test</strong></summary>

The two integration tests use `Base.metadata.create_all()` and do not verify
that Alembic can upgrade a blank database.

This is a conscious lean-testing trade-off.

</details>
