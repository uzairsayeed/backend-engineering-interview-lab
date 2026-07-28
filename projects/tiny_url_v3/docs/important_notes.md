# TinyURL Learning Notes

Learning notes collected across TinyURL V1, V2, and V3.

## Quick navigation

- [V3: Alembic mental model](#v3-alembic-mental-model)
- [V3: Why SQLAlchemy rather than SQLModel?](#v3-why-sqlalchemy-rather-than-sqlmodel)
- [V2: FastAPI and Uvicorn](#v2-fastapi-and-uvicorn)
- [V2: Redirect endpoint structure](#v2-redirect-endpoint-structure)
- [V1: Dependency injection](#v1-dependency-injection)
- [V1: Dependency injection with Protocol](#v1-dependency-injection-with-protocol)
- [V1: Result object vs domain object](#v1-service-return-type-result-object-vs-domain-object)

---

## V3 learnings

<a id="v3-alembic-mental-model"></a>

### V3: Alembic mental model

Run:

```bash
alembic init migrations
```

This creates:

```text
tiny_url_v3/
├── alembic.ini
└── migrations/
    ├── env.py
    ├── README
    ├── script.py.mako
    └── versions/
```

<details open>
<summary><strong>Explore what each generated file does</strong></summary>

#### `alembic.ini`

Alembic configuration.

#### `migrations/env.py`

- Creates the migration environment.
- Loads the database URL.
- Loads SQLAlchemy metadata.

#### `migrations/versions/`

Ordered migration scripts.

#### `script.py.mako`

Template for new revision files.

</details>

<a id="v3-why-sqlalchemy-rather-than-sqlmodel"></a>

### V3: Why SQLAlchemy rather than SQLModel?

FastAPI does not require a particular database library. Its current database
tutorial uses SQLModel, which itself is built on top of SQLAlchemy and Pydantic,
but FastAPI can work directly with SQLAlchemy or other database libraries.

For this project, we’ll use SQLAlchemy directly.

| Library | Role |
| --- | --- |
| SQLModel | Pydantic + SQLAlchemy combined |
| SQLAlchemy | Direct ORM and database toolkit |

This gives us a clearer understanding of:

- ORM models
- Engines
- Connections
- Sessions
- Transactions
- Repository mapping
- Database exceptions
- Persistence boundaries

It also lets us keep these objects separate:

| Object | Responsibility |
| --- | --- |
| `ShortUrl` | Domain model |
| `ShortUrlRecord` | SQLAlchemy persistence model |
| `ShortUrlResponse` | HTTP response model |

That separation will be a major V3 learning outcome.

---

## V2 learnings

<a id="v2-fastapi-and-uvicorn"></a>

### V2: FastAPI and Uvicorn

```text
Internet Request
      ↓
  [ Uvicorn ]   ← listens on a port, speaks HTTP/ASGI
      ↓
  [ FastAPI ]   ← your routes, logic, validation, response
      ↓
  [ Uvicorn ]   ← sends the response back
      ↓
Internet Response
```

| Technology | What it is | Analogy |
| --- | --- | --- |
| FastAPI | Web framework—defines routes and logic | Chef + Menu |
| Uvicorn | ASGI server—handles network connections | Front door + Waitstaff |

FastAPI needs Uvicorn to actually serve the app to the world. FastAPI alone is
just a Python object sitting in memory—Uvicorn is what makes it reachable over
the network.

<details>
<summary><strong>What is ASGI?</strong></summary>

ASGI = Asynchronous Server Gateway Interface.

Think of it like a multi-lane highway with smart traffic management. While
Request 1 is waiting for a database response, Request 2 and 3 are already being
handled.

An ASGI server is a network listener that handles requests asynchronously and
passes them to your Python app using the ASGI standard protocol.

</details>

<a id="v2-redirect-endpoint-structure"></a>

### V2: Redirect endpoint structure

Request:

```http
GET /python
```

The service performs:

```python
short_url = service.resolve_url("python")
```

This:

1. Finds the URL.
2. Rejects a missing URL.
3. Rejects an expired URL.
4. Increments the redirect count.
5. Returns the active mapping.

The HTTP boundary then returns:

```http
HTTP/1.1 307 Temporary Redirect
Location: https://example.com/articles/python
```

There is usually no JSON response here. The important output is the `Location`
header.

FastAPI’s `RedirectResponse` defaults to status 307. HTTP `307 Temporary
Redirect` tells the client to follow the new location while preserving the
original request method.

<details>
<summary><strong>Why not 301 or 308?</strong></summary>

Those communicate a permanent redirect.

A permanent redirect can be aggressively cached by clients or intermediaries.
That becomes inconvenient when:

- The destination changes.
- The short URL is disabled.
- Analytics must record each visit.
- Expiration rules change.

For our application, we choose a temporary redirect.

</details>

#### Possible failures

| Situation | Status |
| --- | --- |
| Short code does not exist | `404 Not Found` |
| Short URL has expired | `410 Gone` |

We use `410 Gone` for expiration because the resource previously existed but is
no longer available for redirecting. HTTP defines both `404 Not Found` and `410
Gone` as distinct client-error statuses.

---

## V1 learnings

<a id="v1-dependency-injection"></a>

### V1: Dependency injection

#### What it means

Do not let a class create its own dependencies. Instead, pass them in from
outside via `__init__`.

<details>
<summary><strong>Compare code without and with dependency injection</strong></summary>

Without DI (bad):

```python
class ShortUrlService:
    def __init__(self):
        self.repository = ShortUrlRepository()  # hardwired, untestable
```

With DI (good):

```python
class ShortUrlService:
    def __init__(self, repository: ShortUrlRepository):
        self.repository = repository  # flexible, testable
```

</details>

#### Where to use it in this project

- `ShortUrlService.__init__` must accept a `ShortUrlRepository` as a parameter.
- Tests create their own fresh repository and inject it:

  ```python
  repo = ShortUrlRepository()
  service = ShortUrlService(repo)
  ```

- This is why every test in `test_repository.py` builds its own
  `ShortUrlRepository()` at the top—each test owns and controls its dependency.

#### Why it matters

- **Testable:** swap the real repository for a fake or mock in tests.
- **Flexible:** swap storage (in-memory → database) without changing service
  code.
- **Loosely coupled:** the service does not care **how** the repository works,
  only **what** it can do.

> **One-line rule:** “Don't build your tools yourself—receive them from whoever
> calls you.”

<a id="v1-dependency-injection-with-protocol"></a>

### V1: Dependency injection with Protocol

#### What it is

Using `Protocol` defines a formal contract (interface) that any repository must
satisfy. The service depends on the contract, not any specific class.

<details open>
<summary><strong>Define and inject the contract</strong></summary>

Define the contract:

```python
from typing import Protocol

class ShortUrlRepositoryProtocol(Protocol):
    def save(self, short_url: ShortUrl) -> ShortUrl: ...
    def get(self, short_code: str) -> ShortUrl | None: ...
    def delete(self, short_code: str) -> bool: ...
```

Inject any implementation:

```python
class ShortUrlService:
    def __init__(self, repository: ShortUrlRepositoryProtocol) -> None:
        self._repository = repository

# All satisfy the Protocol automatically; no inheritance is needed.
ShortUrlService(ShortUrlRepository())          # in-memory
ShortUrlService(PostgresShortUrlRepository())  # real database
ShortUrlService(MockShortUrlRepository())      # for tests
```

</details>

#### Why it is better than basic DI

- Basic DI: the service is still tied to the concrete class in the type hint.
- Protocol DI: the service only knows the contract, not the implementation.
- A type checker (mypy/pyright) validates that any injected class matches the
  contract.
- Storage can be swapped (in-memory → PostgreSQL) without changing service code
  at all.

#### Analogy

- Protocol = USB port (defines the shape it accepts).
- Repositories = USB devices (keyboard, mouse, drive)—anything that fits works.

#### When to use it in this project

- Basic DI is fine for now with one in-memory repository.
- Introduce `Protocol` when switching to a real database or when mocks should be
  formally type-checked.

<a id="v1-service-return-type-result-object-vs-domain-object"></a>

### V1: Service return type—Result Object vs Domain Object

Context: What should `resolve_url()` return?

<details>
<summary><strong>Production-grade: return a dedicated DTO</strong></summary>

Return a dedicated DTO (Data Transfer Object):

```python
@dataclass(frozen=True)
class RedirectResult:
    destination_url: str
    short_code: str
    redirect_count: int
```

Why:

- The caller only gets what it needs (encapsulation).
- It is immutable—`frozen=True` prevents accidental mutation.
- It is decoupled from the domain model—`ShortUrl` can change without breaking
  callers.

</details>

<details>
<summary><strong>Interview-optimised: return the domain object directly</strong></summary>

```python
def resolve_url(self, short_code: str) -> ShortUrl:
    ...
```

Why it is acceptable:

- It is simpler—no extra class is needed.
- `ShortUrl` already has everything the API layer needs.
- Acknowledging the DTO trade-off verbally is enough.

</details>

#### Key rule

> **Production:** The transport layer (what you return) should be independent
> from the domain layer (your model).
>
> **Interview:** Knowing the distinction matters more than implementing it.
