# TinyURL V1 & V2 — Design Decisions and Learning Handbook

> A revision-friendly record of the architecture, trade-offs, concepts, examples, and interview explanations developed while building:
>
> - **TinyURL V1:** plain-Python application core with an interactive CLI
> - **TinyURL V2:** HTTP-only FastAPI application using the same core design principles

---

## How to use this handbook

- Use the **Quick Revision Checklist** before a catch-up or interview.
- Expand the `<details>` sections to review individual design decisions.
- Tick the Markdown checkboxes as you become comfortable explaining each area.
- Use the **Interview Answer Cards** to practise concise explanations.
- Revisit the **Production Gaps** section when moving to SQLAlchemy or a distributed design.

> GitHub, VS Code, Obsidian, Typora, and many Markdown viewers support the collapsible `<details>` elements used throughout this file.

---



## Navigation

- [1. Build summary](#1-build-summary)
- [2. Final architecture](#2-final-architecture)
- [3. Quick revision checklist](#3-quick-revision-checklist)
- [4. V1 plain-Python core decisions](#4-v1-plain-python-core-decisions)
- [5. V2 FastAPI design decisions](#5-v2-fastapi-design-decisions)
- [6. Concepts learned](#6-concepts-learned)
- [7. Important code patterns](#7-important-code-patterns)
- [8. Interview answer cards](#8-interview-answer-cards)
- [9. Common mistakes and corrections](#9-common-mistakes-and-corrections)
- [10. Production limitations and next phase](#10-production-limitations-and-next-phase)
- [11. Final self-review checklist](#11-final-self-review-checklist)

---



# 1. Build summary



## TinyURL V1 — plain Python + CLI

V1 proves that the application logic works independently of any web framework.

Implemented capabilities:

- Create a short URL with a generated code.
- Create a short URL with a custom code.
- Reject duplicate aliases.
- Retry collisions for generated aliases.
- Apply optional expiration.
- Resolve an active URL.
- Reject missing or expired redirects.
- Increment redirect counts.
- Retrieve metadata without incrementing the count.
- List stored URLs.
- Delete stored URLs.
- Run the application through an interactive CLI.
- Test model, repository, and service behaviour.

V1 flow:

```text
Interactive CLI
      ↓
ShortUrlService
      ↓
ShortUrlRepository
      ↓
In-memory dictionary
```



## TinyURL V2 — FastAPI HTTP API

V2 is deliberately **HTTP-only**. The CLI remains a V1 concern.

Implemented endpoints:


| Method   | Endpoint             | Purpose                               |
| -------- | -------------------- | ------------------------------------- |
| `GET`    | `/health`            | Confirm the application is running    |
| `POST`   | `/urls`              | Create a short URL                    |
| `GET`    | `/urls`              | List stored short URLs                |
| `GET`    | `/urls/{short_code}` | Retrieve metadata without redirecting |
| `DELETE` | `/urls/{short_code}` | Delete a short URL                    |
| `GET`    | `/{short_code}`      | Perform a public redirect             |


V2 adds:

- FastAPI and Uvicorn.
- Pydantic request and response schemas.
- Dependency injection using `Depends`.
- Global exception handlers.
- Consistent error responses.
- Redirect responses and cache policy.
- Reserved alias protection.
- Configurable public base URL.
- Practical application logging.
- Focused API tests with dependency overrides.
- `pyproject.toml`, `.env.example`, `.gitignore`, and README documentation.

---



# 2. Final architecture



## Request flow

```text
HTTP client
    ↓
FastAPI route
    ↓
Pydantic validation
    ↓
ShortUrlService
    ↓
ShortUrlRepository
    ↓
In-memory dictionary
    ↓
Domain object
    ↓
Response mapper
    ↓
Pydantic response
    ↓
JSON or RedirectResponse
```



## Layer responsibilities


| Layer                   | Responsibility                              | Must not own                                    |
| ----------------------- | ------------------------------------------- | ----------------------------------------------- |
| `models.py`             | Define `ShortUrl` state and behaviour       | HTTP, route handling, database sessions         |
| `repository.py`         | Store and retrieve `ShortUrl` objects       | Expiration policy, redirects, HTTP status codes |
| `service.py`            | Implement use cases and business rules      | FastAPI-specific types and response objects     |
| `schemas.py`            | Validate and document HTTP data             | Core business workflows                         |
| `routers/`              | Translate HTTP requests into service calls  | Storage rules and domain logic                  |
| `mappers.py`            | Convert domain objects into API responses   | Persistence or business decisions               |
| `exception_handlers.py` | Translate failures into HTTP responses      | Domain-state mutation                           |
| `dependencies.py`       | Create and inject application dependencies  | Business logic                                  |
| `config.py`             | Validate runtime configuration              | Request processing                              |
| `main.py`               | Create and assemble the FastAPI application | Detailed endpoint logic                         |




## Error translation flow

```text
Database/storage language
    ↓
Repository result or repository exception
    ↓
Domain/application language
    ↓
ShortUrlError subtype
    ↓
HTTP language
    ↓
404 / 409 / 410 / 422 / 500 / 503
```

---



# 3. Quick revision checklist



## Plain Python core

- [ ] I can explain why behaviour such as `is_expired()` belongs on `ShortUrl`.
- [ ] I understand why a clock is injected for deterministic tests.
- [ ] I can explain the difference between `None`, `0`, and a positive value in `remaining_seconds()`.
- [ ] I can explain repository versus service responsibilities.
- [ ] I understand why generated-code collisions are retried.
- [ ] I understand why custom-code collisions are not silently changed.
- [ ] I can explain why the repository’s final uniqueness check is necessary.
- [ ] I understand why `get_url_details()` and `resolve_url()` are separate use cases.
- [ ] I can explain why V1 uses `python -m app` as its CLI entry point.



## HTTP and FastAPI

- [ ] I can explain `app.main:app`.
- [ ] I understand the role of Uvicorn and ASGI.
- [ ] I can explain path parameters, request bodies, headers, and status codes.
- [ ] I understand `201 Created`, `204 No Content`, `307 Temporary Redirect`, `409 Conflict`, and `410 Gone`.
- [ ] I can explain why Pydantic request and response models are separate.
- [ ] I understand `Depends`, dependency providers, and dependency overrides.
- [ ] I can explain why one in-memory repository is reused across requests.
- [ ] I understand why `/{short_code}` must be registered after fixed routes.
- [ ] I can explain global exception handlers and safe `500` responses.
- [ ] I understand why the public short-link domain is configuration.
- [ ] I can explain why destination URLs are not logged.



## Interview readiness

- [ ] I can describe the naïve, production-grade, and interview-optimised version of each major decision.
- [ ] I can clearly state the current limitations.
- [ ] I can explain what I would change when adding SQLAlchemy.
- [ ] I can explain why the current design is appropriate for a three-hour exercise.

---



# 4. V1 plain-Python core decisions



## C01. Put domain behaviour on the model

**Decision**: Methods such as `is_expired()`, `record_redirect()`, and `remaining_seconds()` belong on `ShortUrl`.

**Naïve approach**

Keep the dataclass as a passive bag of fields and place all behaviour in unrelated utility functions.

**Production-grade approach**

Use a rich domain model or carefully designed value objects where domain state and valid state transitions are explicit.

**Interview-optimised approach**

Keep small operations that describe one `ShortUrl` on the dataclass itself.

**Chosen because**

These methods operate only on the state of one `ShortUrl` and are easy to test in isolation.

**Trade-off**

The model must not grow into a large object that coordinates repositories, HTTP calls, or infrastructure.

**Interview explanation**

> “I placed state-specific behaviour on the model because expiration and redirect-count mutation describe the object itself. Application workflows remain in the service.”



## C02. Inject time into time-dependent behaviour

**Decision**: Accept `current_time` or inject a clock instead of hardcoding the current time everywhere.

**Naïve approach**

```python
datetime.now(UTC)
```

inside every method and test.

**Production-grade approach**

Use a clock abstraction or dependency throughout application use cases.

**Interview-optimised approach**

- Model methods accept an optional `current_time`.
- The service receives a callable clock.

**Chosen because**

Tests can use an exact timestamp and avoid flaky time-based assertions.

**Example**

```python
FIXED_TIME = datetime(2026, 7, 26, 10, 0, tzinfo=UTC)
service = ShortUrlService(repository, clock=lambda: FIXED_TIME)
```



## C03. Distinguish “never expires” from “already expired”

**Decision**: `remaining_seconds()` returns `None` for no expiration and `0` for an expired URL.


| State                    | Result           |
| ------------------------ | ---------------- |
| No expiration configured | `None`           |
| Expired                  | `0`              |
| Active                   | Positive integer |


**Why**

Returning `0` for both “never expires” and “already expired” loses important meaning.

**Implementation**

```python
def remaining_seconds(
    self,
    current_time: datetime | None = None,
) -> int | None:
    if self.expires_at is None:
        return None

    now = current_time or datetime.now(UTC)
    return max(0, int((self.expires_at - now).total_seconds()))
```



## C04. Keep repository responsibilities narrow

**Decision**: The repository stores and retrieves objects; the service applies use-case rules.

**Repository responsibilities**

- Save.
- Get.
- Check existence.
- List.
- Delete.

**Service responsibilities**

- Calculate expiration.
- Generate aliases.
- Retry generated collisions.
- Reject expired redirects.
- Increment redirect counts.
- Translate missing data into domain errors.

**Avoid**

```python
def get(self, short_code: str) -> ShortUrl:
    # Do not mix lookup, expiry policy, redirect counting,
    # and service-level exceptions here.
```



## C05. Protect uniqueness at the final storage boundary

**Decision**: `save()` rejects duplicate short codes instead of silently overwriting them.

**Why**

A Python dictionary assignment would replace the old destination:

```python
self._urls[short_code] = new_short_url
```

That could unexpectedly redirect an existing public link somewhere else.

**Principle**

```text
Service validation
    → early, friendly check

Repository/database constraint
    → final correctness guarantee
```

**Database equivalent**

A future SQL database should enforce a `UNIQUE` constraint on `short_code`.



## C06. Prefer specific failure information over an ambiguous boolean

**Decision**: Duplicate insertion is represented by a specific exception rather than a generic `False`.

**Boolean problem**

```python
saved = repository.save(short_url)
```

If `False`, why did it fail?

- Duplicate?
- Connection problem?
- Transaction failure?
- Validation issue?

**Chosen approach**

Raise a specific conflict for the known failure.

**Production refinement**

The repository could raise `RepositoryConflictError`, and the service could translate it into `DuplicateShortCodeError`.

**Interview trade-off**

For a three-hour project, directly using `DuplicateShortCodeError` is simpler and still clear.



## C07. Return a boolean from repository deletion

**Decision**: `repository.delete()` returns `bool`; `service.delete_url()` decides whether missing is an error.

**Repository**

```python
def delete(self, short_code: str) -> bool:
    removed = self._urls.pop(short_code, None)
    return removed is not None
```

**Service**

```python
def delete_url(self, short_code: str) -> None:
    if not self._repository.delete(short_code):
        raise ShortCodeNotFoundError(short_code)
```

**Why**

The repository reports a storage fact: nothing was deleted.

The service gives that fact business meaning: the requested URL does not exist.



## C08. Inject the repository into the service

**Decision**: `ShortUrlService` receives its repository through the constructor.

**Naïve**

```python
class ShortUrlService:
    def __init__(self):
        self.repository = ShortUrlRepository()
```

**Problems**

- Harder to test.
- Harder to replace storage.
- Hidden dependency.
- Service controls infrastructure creation.

**Chosen**

```python
repository = ShortUrlRepository()
service = ShortUrlService(repository)
```

**Concept**

Dependency injection.



## C09. Inject code generation and clock as callables

**Decision**: Use small callable dependencies rather than creating full interface classes immediately.

```python
CodeGenerator = Callable[[], str]
Clock = Callable[[], datetime]
```

**Tests**

```python
code_generator=lambda: "abc123"
clock=lambda: FIXED_TIME
```

**Why**

This provides deterministic testing with less boilerplate than separate generator and clock class hierarchies.

**Production option**

Use protocols or explicit strategy interfaces when multiple implementations become significant.



## C10. Save directly instead of relying on check-then-act

**Decision**: Attempt storage and handle a duplicate instead of calling `exists()` as the correctness mechanism.

**Unsafe pattern**

```text
Request A checks: absent
Request B checks: absent
Request A inserts
Request B inserts
```

A preliminary existence check cannot guarantee uniqueness under concurrency.

**Chosen**

```python
try:
    return repository.save(short_url)
except DuplicateShortCodeError:
    # Retry only generated codes.
```

**Principle**

The storage constraint provides the final guarantee.



## C11. Treat custom and generated collisions differently

**Decision**: Retry generated aliases; reject duplicate custom aliases.

**Generated code**

The system chose it, so another code can be generated.

**Custom code**

The user explicitly requested it, so silently replacing it would violate the request.

```text
Generated collision → retry
Custom collision    → 409-style domain conflict
```



## C12. Catch only recoverable exceptions

**Decision**: Retry only `DuplicateShortCodeError`, not every exception.

**Avoid**

```python
except Exception:
    continue
```

That would hide:

- Programming errors.
- Storage outages.
- Invalid state.
- Unexpected runtime failures.

**Chosen**

```python
except DuplicateShortCodeError:
    continue
```

**Principle**

Catch an exception only when the current layer can handle it meaningfully.



## C13. Separate metadata retrieval from redirect resolution

**Decision**: Use `get_url_details()` for inspection and `resolve_url()` for redirection.


| Use case            | Missing | Expired | Count mutation |
| ------------------- | ------- | ------- | -------------- |
| `get_url_details()` | Error   | Allowed | No             |
| `resolve_url()`     | Error   | Error   | Increment      |


**Why**

An administrator should be able to inspect an expired URL without recording a redirect.



## C14. Use object mutation only because V1 storage holds the same reference

**Decision**: In-memory redirect counting mutates the retrieved object directly.

```python
short_url.record_redirect()
```

This works because the dictionary stores the same object reference.

**Production change**

A database implementation should use an atomic update such as:

```sql
UPDATE short_urls
SET redirect_count = redirect_count + 1
WHERE short_code = :short_code;
```



## C15. Give V1 an explicit CLI entry point

**Decision**: Run V1 with `python -m app` using `app/__main__.py`.

```text
python -m app
    ↓
app/__main__.py
    ↓
cli.run()
```

**Why**

- Keeps executable code out of model and service modules.
- Prevents code from running on import.
- Makes the composition root explicit.
- Uses one repository and service for the CLI process lifetime.



---



# 5. V2 FastAPI design decisions



## Decisions 1–9: HTTP contract and application startup

**Decision 1**: Use resource-oriented routes.

**Naïve:** `/create-url`, `/get-url`, `/delete-url`

**Production:** Versioned and ownership-scoped resources such as `/v1/users/{user_id}/urls`

**Interview-optimised:** `/urls` and `/urls/{short_code}`

**Why:** Clear REST-style naming without premature versioning or tenancy complexity.



**Decision 2**: Separate metadata retrieval and public redirect routes.

```text
GET /urls/{short_code} → details
GET /{short_code}      → redirect
```

**Why:** Metadata reads remain read-only and do not alter analytics.



**Decision 3**: Use `307 Temporary Redirect`.

**Naïve:** Use the framework default without understanding it.

**Production:** Choose among `301`, `302`, `307`, and `308` based on caching, SEO, and method semantics.

**Interview-optimised:** `307`

**Why:** Temporary and method-preserving; suitable while destinations and link lifecycle may change.



**Decision 4**: Return `204 No Content` after successful deletion.

**Why:** The delete operation succeeds synchronously and no representation needs to be returned.

**Rule:** A `204` response should contain no body.



**Decision 5**: Distinguish missing and expired redirects.

```text
Missing → 404 Not Found
Expired → 410 Gone
```

**Why:** Expired means the link previously existed but is no longer available for redirecting.



**Decision 6**: Keep TinyURL V2 HTTP-only.

```text
V1 → interactive CLI
V2 → FastAPI HTTP API
```

**Why:** Avoid mixing unrelated adapters and keep the FastAPI exercise focused.



**Decision 7**: Use Uvicorn and `app.main:app` as the entry point.

```bash
uvicorn app.main:app --reload
```

```text
app.main → Python module
app      → FastAPI object inside that module
```



**Decision 8**: Start small and split routes when justified.

**Naïve:** Put everything permanently in `main.py`.

**Production:** Versioned routers grouped by bounded context.

**Interview-optimised:** Keep `/health` in `main.py`; move URL operations into routers once multiple endpoints exist.



**Decision 9**: Use synchronous route handlers until async I/O is introduced.

**Why:** `async def` is not automatically better. Use it when the called libraries perform asynchronous I/O.



## Decisions 10–15: Pydantic and validation

**Decision 10**: Use Pydantic models instead of raw dictionaries.

**Benefits**

- Runtime validation.
- Type conversion.
- Structured errors.
- OpenAPI documentation.
- Editor support.



**Decision 11**: Keep request and response models separate.

```text
CreateShortUrlRequest
    destination_url
    custom_code
    expires_in_seconds

ShortUrlResponse
    short_code
    destination_url
    short_url
    created_at
    expires_at
    redirect_count
```

**Why:** Clients must not set server-controlled fields.



**Decision 12**: Validate destination URLs with `HttpUrl`.

**Boundary**

```python
destination_url: HttpUrl
```

**Service**

```python
destination_url=str(payload.destination_url)
```

**Why:** Pydantic remains at the HTTP boundary; the service receives plain Python types.



**Decision 13**: Constrain custom aliases at the HTTP boundary.

Interview rules:

- Minimum 3 characters.
- Maximum 32 characters.
- Letters, numbers, `_`, and `-`.

**Production extension**

Reserved words, Unicode policy, normalisation, tenancy, and case rules could move into a domain value object.



**Decision 14**: Reject unknown request fields.

```python
ConfigDict(extra="forbid")
```

**Why:** A typo such as `custm_code` should fail instead of being silently ignored.



**Decision 15**: Split validation ownership.

```text
Pydantic:
    shape, type, basic format

Service:
    uniqueness, expiration rules, use-case invariants
```

**Why:** The service remains protected when called outside HTTP.



## Decisions 16–19: Dependency injection and lifetime

**Decision 16**: Reuse one in-memory repository and service per application process.

**Why:** Separate HTTP requests must see the same data.

**Limitation:** Multiple worker processes would still hold separate dictionaries.



**Decision 17**: Inject the service into routes using FastAPI `Depends`.

**Why**

- Routes do not construct infrastructure.
- Tests can override the service.
- Business logic remains behind the service layer.



**Decision 18**: Routes depend on the service, not the repository.

**Why:** Direct repository access could bypass expiration, collision, redirect-count, and deletion rules.



**Decision 19**: Use an `Annotated` dependency alias.

```python
ShortUrlServiceDependency = Annotated[
    ShortUrlService,
    Depends(get_short_url_service),
]
```

**Why:** Avoid repetitive dependency syntax while preserving type information.



## Decisions 20–25: Creation endpoint

**Decision 20**: Move URL routes into `routers/urls.py`.

**Why:** The resource now has enough operations to justify a focused router.



**Decision 21**: Map domain objects into response schemas using a reusable function.

```text
ShortUrl
    ↓
to_short_url_response()
    ↓
ShortUrlResponse
```

**Why:** Avoid leaking internal models and repeating field construction.



**Decision 22**: Initially construct the public link from the request base URL.

**Trade-off:** This can be wrong behind reverse proxies or gateways.

**Later improvement:** Replaced by configured `public_base_url` in Decision 54.



**Decision 23**: Handle domain errors centrally.

**Naïve:** `try/except` in every route.

**Chosen:** Register one handler for the `ShortUrlError` hierarchy.

**Why:** Routes remain focused on successful execution.



**Decision 24**: Return `201 Created` and a `Location` header.

```http
Location: /urls/python
```

The header points to the metadata resource, not the public redirect action.



**Decision 25**: Give every API test a fresh service and repository.

**Mechanism:** FastAPI dependency overrides.

**Why:** Tests remain independent, while multiple requests inside one test share state.



## Decisions 26–30: Metadata endpoint

**Decision 26**: Use a dedicated metadata use case.

`GET /urls/{short_code}` calls `get_url_details()`, not `resolve_url()`.



**Decision 27**: Validate path parameters using shared constraints.

**Why:** Avoid one short-code rule in request bodies and another in route paths.

**Trade-off:** Full unification would require a domain value object.



**Decision 28**: Allow expired URL metadata to be retrieved.

Expiration controls public redirection, not administrative visibility.



**Decision 29**: Reuse the same response mapper across create, details, and list endpoints.

**Why:** One representation and one URL-construction rule.



**Decision 30**: Seed specialised test states through a repository fixture.

**Why:** Tests can create expired records without accessing private service attributes.



## Decisions 31–36: Redirect endpoint

**Decision 31**: Return a real `RedirectResponse`, not JSON.

```http
HTTP/1.1 307 Temporary Redirect
Location: https://example.com
```



**Decision 32**: Return `Cache-Control: no-store` for redirects.

**Why:** Every request should reach the application for expiration checks and redirect-count updates.

**Production alternative:** CDN caching with analytics captured separately.



**Decision 33**: Reserve application route names as unavailable aliases.

Examples:

- `health`
- `urls`
- `docs`
- `redoc`
- `openapi.json`

**Why:** A created short code must be reachable.



**Decision 34**: Retry generated reserved codes but reject custom reserved codes.

```text
Generated reserved code → retry
Custom reserved code    → conflict
```



**Decision 35**: Register the catch-all redirect route last.

`/{short_code}` can match `/health`, `/docs`, or other one-segment paths.

Fixed routes must receive priority.



**Decision 36**: Preserve the `404` versus `410` distinction for public redirects.

This keeps lifecycle information meaningful to clients and reviewers.



## Decisions 37–42: List and delete endpoints

**Decision 37**: Return `200 []` for an empty collection.

The `/urls` collection exists even when it contains no items.



**Decision 38**: Return a raw list until pagination is introduced.

```python
response_model=list[ShortUrlResponse]
```

**Future:** Use an envelope containing `items`, `total`, and a cursor or offset.



**Decision 39**: Do not promise list ordering yet.

**Why:** Insertion order is an implementation detail. A database version should use explicit `ORDER BY` when ordering becomes part of the contract.



**Decision 40**: Use `204 No Content` for synchronous deletion.

No success message is required because the status code already communicates success.



**Decision 41**: Use strict deletion semantics.

```text
Existing URL → 204
Missing URL  → 404
```

**Alternative:** An idempotent API could return success for an already-missing resource.



**Decision 42**: Allow expired URLs to be deleted.

Expiration prevents redirecting; it does not prevent administrative management.



## Decisions 43–48: Consistent errors

**Decision 43**: Standardise FastAPI validation errors into the application error format.

```json
{
  "error": {
    "code": "request_validation_failed",
    "message": "Request validation failed",
    "details": []
  }
}
```



**Decision 44**: Return structured validation issues.

Each issue contains:

- `location`
- `message`
- `type`

**Why:** Clients can identify the exact invalid field.



**Decision 45**: Do not echo invalid input values in public errors.

**Why:** Inputs may include tokens, personal data, private URLs, or large payloads.



**Decision 46**: Hide unexpected exception details from clients.

**Client**

```json
{
  "error": {
    "code": "internal_server_error",
    "message": "An unexpected error occurred"
  }
}
```

**Engineering logs**

Contain the full traceback.



**Decision 47**: Standardise framework-generated `404` and `405` errors.

**Why:** Unknown routes and unsupported methods should follow the same public error contract.



**Decision 48**: Register one application-level unexpected-exception handler.

**Avoid:** `except Exception` inside every route.

**Why:** Centralisation prevents duplicated logic and accidental information leakage.



## Decisions 49–53: Testing scope

**Decision 49**: Keep focused tests and defer the full lifecycle suite.

**Chosen scope**

- Model tests.
- Repository tests.
- Service tests.
- Schema tests.
- Focused endpoint tests.
- Error-handler tests.

**Deferred**

- Full create-to-delete lifecycle test.
- Additional helper and isolation files.
- Expanded API-level collision scenarios.

**Why:** The project was becoming cognitively overwhelming, and the current tests already cover the important learning goals.



**Decision 50**: Focused tests remain the primary test style.

**Why:** When one behaviour fails, the source is easier to identify.

**Deferred idea:** One end-to-end lifecycle test can be added later.



**Decision 51**: Test isolation is achieved through dependency fixtures, without adding a separate isolation suite.

The existing fixture creates a fresh repository per test.



**Decision 52**: Deterministic generators remain the strategy for collision tests.

```python
code_generator=lambda: "abc123"
```

or:

```python
generated_codes = iter(["taken", "available"])
```



**Decision 53**: Avoid unnecessary test-helper abstraction for now.

**Why:** Helpers are useful only when they reduce repetition without hiding important test behaviour.



## Decisions 54–58: Configuration

**Decision 54**: Configure one canonical public base URL.

```text
Local:      http://127.0.0.1:8000
Production: https://go.company.com
```

**Why:** Internal container or proxy hostnames must not appear in returned links.



**Decision 55**: Read configuration from environment variables and an optional `.env`.

**Why:** The same code can run in local, test, and production environments.



**Decision 56**: Cache the settings dependency.

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Why:** Read and validate configuration once while keeping it overrideable in tests.



**Decision 57**: Validate configuration types.

```python
public_base_url: AnyHttpUrl
```

**Why:** Fail during startup rather than generating malformed URLs later.



**Decision 58**: Prefer configured public URLs over blindly trusting `request.base_url`.

**Production nuance:** Trusted proxy headers and custom-domain routing may still be required.



## Decisions 59–63: Logging

**Decision 59**: Use Python’s standard `logging` module.

**Why:** Severity levels, formatting, module loggers, and tracebacks without another dependency.



**Decision 60**: Keep Uvicorn access logs instead of adding custom request middleware.

```text
Access log      → HTTP request and status
Application log → meaningful business event
```



**Decision 61**: Log individual redirects at `DEBUG`.

**Why:** Redirect traffic can be high-volume and should not flood normal operational logs.



**Decision 62**: Do not log destination URLs by default.

URLs may contain:

- Tokens.
- Query parameters.
- Customer identifiers.
- Private document references.

Log short codes and event metadata instead.



**Decision 63**: Use FastAPI lifespan for startup and shutdown events.

**Why:** This is the correct place to initialise and later close shared resources such as database pools.



## Decisions 64–68: Packaging and documentation

**Decision 64**: Declare dependencies in `pyproject.toml`.

**Why:** One reproducible command installs the project.



**Decision 65**: Separate runtime and development dependencies.

```bash
python -m pip install -e ".[dev]"
```

Runtime:

- FastAPI.
- Pydantic Settings.

Development:

- pytest.
- HTTP test support.
- Ruff.



**Decision 66**: Keep pytest and Ruff configuration in `pyproject.toml`.

**Why:** Tool configuration is easy to discover and version-control.



**Decision 67**: Keep the README concise and operational.

It documents:

- Setup.
- Run commands.
- Endpoints.
- Example requests.
- Tests.
- Formatting.
- Current limitations.



**Decision 68**: Defer dependency lock-file tooling.

**Trade-off:** Fresh installations may receive newer compatible versions.

**Revisit:** Before deployment or multi-developer collaboration.



---



# 6. Concepts learned



## Python and application design


| Concept              | Short description                                        | Small example                             |
| -------------------- | -------------------------------------------------------- | ----------------------------------------- |
| Dataclass            | Generates common model methods for data-holding classes  | `@dataclass class ShortUrl: ...`          |
| Type hint            | Documents and supports checking of expected types        | `expires_at: datetime | None`             |
| Optional value       | A field may contain a value or `None`                    | `int | None`                              |
| UTC-aware datetime   | A timestamp with explicit timezone information           | `datetime.now(UTC)`                       |
| Domain model         | Represents business state and object-specific behaviour  | `ShortUrl.is_expired()`                   |
| Repository           | Abstracts storage and retrieval                          | `repository.get("python")`                |
| Service layer        | Coordinates application use cases and rules              | `service.resolve_url("python")`           |
| Dependency injection | Supplies dependencies from outside the component         | `ShortUrlService(repository)`             |
| Callable dependency  | A function injected as a strategy                        | `clock=lambda: FIXED_TIME`                |
| Protocol             | Structural interface for interchangeable implementations | `class RepositoryProtocol(Protocol): ...` |
| Exception hierarchy  | Groups related failures under a base type                | `ShortUrlError`                           |
| Object identity      | Checks whether two names point to the same object        | `first is second`                         |
| Composition root     | Place where concrete objects are created and connected   | `dependencies.py`                         |
| List comprehension   | Builds a list by transforming an iterable                | `[mapper(item) for item in items]`        |
| `casefold()`         | Normalises strings for case-insensitive comparison       | `"Health".casefold()`                     |
| Fail fast            | Reject invalid state/configuration early                 | Invalid settings prevent startup          |




## HTTP concepts


| Concept             | Short description                                                  | Small example                    |
| ------------------- | ------------------------------------------------------------------ | -------------------------------- |
| HTTP request        | Client message containing method, path, headers, and optional body | `POST /urls`                     |
| HTTP response       | Server result containing status, headers, and optional body        | `201 Created`                    |
| Resource            | Entity represented by an HTTP address                              | `/urls/python`                   |
| Collection endpoint | Represents multiple resources                                      | `GET /urls`                      |
| Item endpoint       | Represents one identified resource                                 | `GET /urls/python`               |
| Path parameter      | Dynamic value embedded in a path                                   | `/{short_code}`                  |
| Request body        | Structured input, commonly JSON                                    | `{"destination_url": "..."}`     |
| Header              | Metadata attached to a request or response                         | `Location`, `Cache-Control`      |
| Status code         | Numeric outcome of an HTTP operation                               | `404`, `409`, `422`              |
| Idempotency         | Repeating an operation has the same intended effect                | `DELETE /urls/python`            |
| Redirect            | Tells the client to request another location                       | `307 + Location`                 |
| Response caching    | Reuse of a stored HTTP response                                    | Cached redirect                  |
| `204 No Content`    | Successful response with no body                                   | Successful deletion              |
| `410 Gone`          | Resource previously existed but is no longer available             | Expired link                     |
| Route precedence    | Order in which matching routes are considered                      | `/health` before `/{short_code}` |
| Reserved identifier | Valid-looking value unavailable because the app uses it            | `health`, `docs`                 |




## FastAPI and Pydantic


| Concept                  | Short description                                       | Small example                            |
| ------------------------ | ------------------------------------------------------- | ---------------------------------------- |
| Framework                | Provides structure and invokes application code         | FastAPI calls route handlers             |
| ASGI                     | Interface between Python async servers and applications | Uvicorn ↔ FastAPI                        |
| Uvicorn                  | ASGI server that listens for HTTP traffic               | `uvicorn app.main:app`                   |
| Path operation           | Method + path + handler                                 | `@app.get("/health")`                    |
| Decorator                | Registers or modifies a function                        | `@router.post("")`                       |
| Serialisation            | Converts Python values into JSON-compatible output      | Dict → JSON                              |
| Pydantic model           | Typed validation and serialisation class                | `class CreateShortUrlRequest(BaseModel)` |
| Schema                   | Formal data shape and constraints                       | OpenAPI request schema                   |
| DTO                      | Object carrying data across a boundary                  | `ShortUrlResponse`                       |
| `Annotated`              | Adds metadata or validation to a Python type            | `Annotated[str, Path(...)]`              |
| `Field`                  | Adds validation and documentation rules                 | `Field(gt=0)`                            |
| `ConfigDict`             | Configures Pydantic model behaviour                     | `extra="forbid"`                         |
| `HttpUrl`                | Validated HTTP/HTTPS URL type                           | `destination_url: HttpUrl`               |
| `response_model`         | Declares and filters public output shape                | `ShortUrlResponse`                       |
| `APIRouter`              | Groups related routes                                   | `router = APIRouter(prefix="/urls")`     |
| `Depends`                | Declares a FastAPI dependency                           | `Depends(get_service)`                   |
| Dependency provider      | Callable that returns a dependency                      | `get_short_url_service()`                |
| Dependency override      | Replaces a dependency in tests                          | `app.dependency_overrides[...]`          |
| `RequestValidationError` | FastAPI error for invalid incoming data                 | Invalid URL → `422`                      |
| Exception handler        | Converts an exception into an HTTP response             | Domain error → `409`                     |
| `RedirectResponse`       | Response object producing an HTTP redirect              | `RedirectResponse(url=...)`              |
| `TestClient`             | In-process HTTP-style test client                       | `client.post("/urls", json=...)`         |
| Lifespan                 | Startup-to-shutdown application context                 | Code before/after `yield`                |




## Configuration, logging, and packaging


| Concept                   | Short description                                       | Small example                          |
| ------------------------- | ------------------------------------------------------- | -------------------------------------- |
| Application configuration | Runtime values separated from source code               | Public base URL                        |
| Environment variable      | Value supplied to the process environment               | `TINYURL_LOG_LEVEL=DEBUG`              |
| `.env` file               | Local environment-style configuration file              | `TINYURL_PUBLIC_BASE_URL=...`          |
| `BaseSettings`            | Typed settings loaded from environment                  | `class Settings(BaseSettings)`         |
| Configuration prefix      | Prefix preventing variable-name collisions              | `TINYURL_`                             |
| Cached dependency         | Reused dependency result                                | `@lru_cache`                           |
| Logger                    | Named object emitting log records                       | `logging.getLogger("tinyurl.service")` |
| Log level                 | Severity of an event                                    | `DEBUG`, `INFO`, `ERROR`               |
| Handler                   | Destination for logs                                    | `StreamHandler()`                      |
| Formatter                 | Output shape of a log record                            | timestamp + level + message            |
| Logger hierarchy          | Child loggers inherit parent configuration              | `tinyurl.service`                      |
| Access log                | HTTP request and response status record                 | `POST /urls → 201`                     |
| Business-event log        | Domain-relevant application event                       | `short_url_deleted`                    |
| `pyproject.toml`          | Standard Python project metadata and tool configuration | Dependencies + Ruff + pytest           |
| Runtime dependency        | Required to run the app                                 | FastAPI                                |
| Dev dependency            | Required for development/testing                        | pytest, Ruff                           |
| Editable install          | Uses source directly from working directory             | `pip install -e ".[dev]"`              |
| Linter                    | Detects likely code and style problems                  | `ruff check .`                         |
| Formatter                 | Applies consistent formatting                           | `ruff format .`                        |


---



# 7. Important code patterns



## 7.1 Model with deterministic time handling

```python
@dataclass
class ShortUrl:
    short_code: str
    destination_url: str
    created_at: datetime
    expires_at: datetime | None = None
    redirect_count: int = 0

    def is_expired(
        self,
        current_time: datetime | None = None,
    ) -> bool:
        if self.expires_at is None:
            return False

        now = current_time or datetime.now(UTC)
        return self.expires_at <= now

    def record_redirect(self) -> None:
        self.redirect_count += 1
```



## 7.2 Repository deletion contract

```python
def delete(self, short_code: str) -> bool:
    deleted = self._urls.pop(short_code, None)
    return deleted is not None
```



## 7.3 Service translation

```python
def delete_url(self, short_code: str) -> None:
    if not self._repository.delete(short_code):
        raise ShortCodeNotFoundError(short_code)
```



## 7.4 Generated-code collision handling

```python
for _ in range(self._max_generation_attempts):
    generated_code = self._code_generator()

    if self._is_reserved_short_code(generated_code):
        continue

    try:
        return self._repository.save(
            ShortUrl(
                short_code=generated_code,
                destination_url=destination_url,
                created_at=created_at,
                expires_at=expires_at,
            )
        )
    except DuplicateShortCodeError:
        continue

raise ShortCodeGenerationError(
    self._max_generation_attempts
)
```



## 7.5 FastAPI dependency alias

```python
ShortUrlServiceDependency = Annotated[
    ShortUrlService,
    Depends(get_short_url_service),
]
```



## 7.6 Request schema

```python
class CreateShortUrlRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    destination_url: HttpUrl
    custom_code: ShortCode | None = None
    expires_in_seconds: int | None = Field(
        default=None,
        gt=0,
    )
```



## 7.7 Response mapping

```python
def to_short_url_response(
    short_url: ShortUrl,
    public_base_url: str,
) -> ShortUrlResponse:
    base = public_base_url.rstrip("/")

    return ShortUrlResponse(
        short_code=short_url.short_code,
        destination_url=short_url.destination_url,
        short_url=f"{base}/{short_url.short_code}",
        created_at=short_url.created_at,
        expires_at=short_url.expires_at,
        redirect_count=short_url.redirect_count,
    )
```



## 7.8 Redirect route

```python
@router.get(
    "/{short_code}",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
def redirect_short_url(
    short_code: ShortCodePath,
    service: ShortUrlServiceDependency,
) -> RedirectResponse:
    short_url = service.resolve_url(short_code)

    return RedirectResponse(
        url=short_url.destination_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Cache-Control": "no-store"},
    )
```



## 7.9 Safe unexpected-error response

```python
async def handle_unexpected_error(
    request: Request,
    error: Exception,
) -> JSONResponse:
    logger.exception(
        "unhandled_exception method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=error,
    )

    return build_error_response(
        status_code=500,
        code="internal_server_error",
        message="An unexpected error occurred",
    )
```



## 7.10 Settings dependency

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---



# 8. Interview answer cards

**Why did you use a service layer?**

> “The service layer contains application use cases such as creating, resolving, inspecting, and deleting short URLs. It prevents HTTP routes from directly depending on persistence and keeps business rules reusable outside FastAPI.”



**Why did you inject the repository?**

> “Constructor injection makes the dependency explicit, allows the service to work with an in-memory or database repository, and lets tests provide deterministic storage without changing business logic.”



**Why does the repository still check duplicates?**

> “A service-level check can improve the error experience, but it cannot provide a concurrency guarantee. The final uniqueness guarantee must exist at the storage boundary, which would become a database unique constraint in production.”



**Why not call** `exists()` **before saving?**

> “That creates a check-then-act race. Two requests can both observe that the alias is absent. I attempt the insert and handle the specific duplicate conflict instead.”



**Why are custom and generated aliases handled differently?**

> “A generated alias is replaceable, so a collision can be retried. A custom alias represents the user’s explicit request, so silently replacing it would be incorrect; I return a conflict instead.”



**Why separate metadata retrieval and redirect?**

> “The metadata endpoint is a read-only administrative query. The redirect use case applies expiration rules and increments analytics. Combining them would make a metadata read mutate state.”



**Why use** `307`**?**

> “The redirect is temporary and may later change or expire. `307` also preserves the request method. For a simple GET short-link flow, it is a clear and defensible temporary redirect choice.”



**Why return** `410` **for expired links?**

> “`404` represents a missing resource, while `410` communicates that the resource existed but is no longer available. That distinction matches the link lifecycle.”



**Why use response models instead of returning the dataclass?**

> “The API contract should be independent of the internal domain model. A response model prevents accidental field leakage and allows computed HTTP fields such as the public short URL.”



**Why validate in both Pydantic and the service?**

> “Pydantic protects the HTTP boundary and gives clients structured feedback. The service still enforces business invariants because it may be called by tests, workers, or future adapters that bypass HTTP.”



**Why one global in-memory repository?**

> “For this phase, it allows separate requests in one process to share state. I would not use it with multiple workers; the database phase replaces it with shared persistence.”



**Why dependency overrides in tests?**

> “Production routes keep the normal dependency contract, while each test injects a fresh deterministic service and repository. This prevents state leakage and avoids modifying route code for tests.”



**Why a configured public base URL?**

> “The internal application hostname can differ from the public domain behind a proxy or gateway. A validated canonical URL ensures responses contain the address users can actually access.”



**Why not log destination URLs?**

> “URLs frequently contain sensitive query parameters or identifiers. I log short codes and event metadata, which are operationally useful without unnecessarily copying user input.”



**What would you change for production?**

> “I would add persistent storage, a database unique constraint, transaction management, atomic redirect counters, pagination, authentication and ownership, rate limiting, abuse protection, structured observability, and a deployment-ready dependency lock and container setup.”



---



# 9. Common mistakes and corrections


| Mistake                                                  | Why it is problematic                             | Correction                              |
| -------------------------------------------------------- | ------------------------------------------------- | --------------------------------------- |
| Returning `0` when a URL never expires                   | Confuses “never expires” with “expired”           | Return `None` for no expiration         |
| Letting dictionary assignment overwrite a duplicate      | Existing links change destination silently        | Reject duplicate codes                  |
| Returning `False` for every save failure                 | Loses the failure reason                          | Use specific exceptions                 |
| Raising domain expiration errors from repository `get()` | Repository starts enforcing use-case policy       | Apply expiration in service             |
| Creating a repository per request                        | Every request sees empty state                    | Reuse app-scoped in-memory repository   |
| Calling `resolve_url()` from metadata endpoint           | Increments analytics and rejects expired metadata | Call `get_url_details()`                |
| Returning the dataclass directly                         | Couples API to internals                          | Map to a response schema                |
| Returning `200` after creation by default                | Does not communicate resource creation            | Use `201`                               |
| Returning a JSON body with `204`                         | Violates the intended response semantics          | Return an empty `Response`              |
| Registering `/{short_code}` before `/health`             | Dynamic route captures fixed paths                | Register catch-all last                 |
| Allowing `health` as a custom alias                      | Generated link cannot be reached                  | Reserve application routes              |
| Catching `Exception` in every route                      | Repetition and error leakage                      | Use global handlers                     |
| Returning `str(error)` for unexpected failures           | Leaks internal information                        | Log traceback, return safe `500`        |
| Trusting `request.base_url` in every environment         | Proxy/internal host may leak                      | Configure canonical public URL          |
| Logging complete destination URLs                        | May expose sensitive data                         | Log short code and event metadata       |
| Using `async def` everywhere                             | Adds no value without async I/O                   | Choose sync/async based on dependencies |
| Depending on test execution order                        | Tests become flaky                                | Fresh repository per test               |
| Overbuilding lifecycle tests too early                   | Cognitive overload                                | Keep focused tests; defer extras        |


---



# 10. Production limitations and next phase



## Current intentional limitations

- Data exists only in memory.
- All data is lost when the process restarts.
- Multiple workers do not share data.
- Redirect count updates are not database-atomic.
- Listing has no pagination.
- There is no authentication.
- There is no ownership model.
- There is no rate limiting.
- There is no phishing or malware protection.
- There is one public domain.
- Short-code case sensitivity is not fully product-defined.
- Dependency versions are not locked.
- Logging is text-based, not structured JSON.
- There are no correlation IDs or distributed traces.



## Recommended Phase 3 roadmap: SQLAlchemy persistence

- [ ] Define an SQLAlchemy ORM model.
- [ ] Add SQLite for local development.
- [ ] Introduce database sessions.
- [ ] Define transaction boundaries.
- [ ] Add a database unique constraint for `short_code`.
- [ ] Translate `IntegrityError` into repository conflict semantics.
- [ ] Add repository protocol or interface.
- [ ] Keep in-memory and SQL implementations interchangeable.
- [ ] Persist redirect counts.
- [ ] Implement an atomic redirect-count update.
- [ ] Add Alembic migrations.
- [ ] Add repository integration tests.
- [ ] Add pagination and explicit ordering.
- [ ] Revisit application lifespan for database engine setup and disposal.



## Scaling discussion

```text
Client
  ↓
Load balancer
  ↓
Multiple API workers
  ↓
Shared database
  ↓
Optional Redis/cache
  ↓
Asynchronous analytics pipeline
```

Potential production split:

```text
Public redirect service
    Optimised for very high read traffic

Management API
    Create, inspect, list, and delete links

Analytics pipeline
    Records redirect events asynchronously
```

---



# 11. Final self-review checklist



## Architecture

- [ ] Every file has one clear responsibility.
- [ ] Routes call services, not repositories.
- [ ] The service contains business workflows.
- [ ] The repository contains storage operations.
- [ ] Pydantic types do not leak into the service.
- [ ] HTTP exceptions do not leak into the domain layer.



## API

- [ ] `POST /urls` returns `201`.
- [ ] `Location` points to `/urls/{short_code}`.
- [ ] `GET /urls/{short_code}` does not increment the count.
- [ ] `GET /{short_code}` returns `307`.
- [ ] Redirects include `Cache-Control: no-store`.
- [ ] Expired redirects return `410`.
- [ ] Missing resources return `404`.
- [ ] Duplicate or reserved aliases return `409`.
- [ ] Successful deletion returns an empty `204`.
- [ ] Invalid input uses the common `422` error contract.



## Testing

- [ ] Model tests pass.
- [ ] Repository tests pass.
- [ ] Service tests pass.
- [ ] Schema tests pass.
- [ ] Focused API tests pass.
- [ ] Dependency overrides are cleared.
- [ ] Redirect tests disable automatic redirect following.
- [ ] Unexpected errors are tested with safe public output.



## Configuration and operations

- [ ] `.env.example` exists.
- [ ] `.env` is ignored.
- [ ] `public_base_url` is validated.
- [ ] Log level is configurable.
- [ ] Startup and shutdown are logged.
- [ ] Destination URLs are not logged.
- [ ] `pyproject.toml` contains dependencies and tool configuration.
- [ ] README contains setup and run commands.



## Commands

```bash
python -m pip install -e ".[dev]"
python -m pytest
ruff check .
ruff format --check .
uvicorn app.main:app --reload
```

---



## Final one-minute project explanation

> “I built the application in two stages. V1 established a framework-independent Python core using a domain model, repository, service layer, injected clock and code generator, explicit exceptions, and an interactive CLI. V2 exposed the same design through an HTTP-only FastAPI application. Pydantic validates external input, routes call injected services, mappers control output, and global handlers translate domain and framework failures into a consistent API contract. The in-memory repository is deliberately application-process scoped for this learning phase, with configuration, logging, focused tests, and packaging added around it. The next production step is replacing the dictionary with a transactional SQLAlchemy repository and atomic database operations.”

