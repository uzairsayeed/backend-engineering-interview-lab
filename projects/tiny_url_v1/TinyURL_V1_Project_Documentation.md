# TinyURL V1 — Project Documentation

## 1. Requirements

### 1.1 Functional Requirements

TinyURL V1 is a plain-Python, in-memory URL-shortening application accessed through an interactive command-line interface.

The application must support the following operations:

1. **Create a short URL**
   - Accept a destination URL.
   - Accept an optional custom short code.
   - Generate a random short code when a custom code is not supplied.
   - Reject duplicate custom short codes.
   - Retry when an automatically generated code collides with an existing code.
   - Support an optional expiration duration.

2. **Resolve a short URL**
   - Retrieve a short URL by its short code.
   - Reject unknown short codes.
   - Reject expired short URLs.
   - Increment the redirect count only for successful resolutions.
   - Return the destination URL.

3. **View URL details**
   - Retrieve a stored short URL without incrementing its redirect count.
   - Allow expired URLs to be inspected.
   - Reject unknown short codes.

4. **List all short URLs**
   - Return all URLs currently stored in the repository.

5. **Delete a short URL**
   - Remove an existing URL.
   - Raise a domain-level not-found error when the requested short code does not exist.

6. **Interactive CLI**
   - Present a menu for create, resolve, view, list, delete and exit operations.
   - Display domain errors in a user-friendly form.
   - Exit cleanly when the user selects Exit.

### 1.2 Data Requirements

Each short URL contains:

```python
short_code: str
destination_url: str
created_at: datetime
expires_at: datetime | None
redirect_count: int
```

All application timestamps are timezone-aware and use UTC:

```python
datetime.now(UTC)
```

### 1.3 Current V1 Limitations

- Data is stored only in memory.
- All data is lost when the application process exits.
- URL format validation is minimal and will later be handled at the FastAPI/Pydantic boundary.
- Redirect-count updates are safe for the current single-process in-memory implementation but are not yet atomic for concurrent database usage.
- There is no authentication, authorisation, rate limiting or persistent analytics.
- The application is accessed through a CLI rather than HTTP.

---

## 2. Architecture

### 2.1 Layered Architecture

```text
Interactive CLI
      |
      v
ShortUrlService
      |
      v
ShortUrlRepository
      |
      v
In-memory dictionary

ShortUrl model is used by both the service and repository.
Domain exceptions communicate expected failure states.
```

### 2.2 Responsibilities

#### `models.py`

Defines what a `ShortUrl` is and the behaviour that belongs to its own state.

Responsibilities:

- Store short URL data.
- Determine whether the URL is expired.
- Increment redirect count.
- Calculate remaining expiration time.

Example methods:

```python
is_expired()
record_redirect()
remaining_seconds()
```

#### `repository.py`

Defines how `ShortUrl` objects are stored and retrieved.

Responsibilities:

- Save a URL.
- Retrieve a URL.
- Check whether a code exists.
- List all URLs.
- Delete a URL.
- Protect against duplicate keys in the in-memory store.

The repository does not decide whether an expired URL may be resolved or inspected.

#### `service.py`

Defines application use cases and business rules.

Responsibilities:

- Create short URLs.
- Generate codes.
- Retry generated-code collisions.
- Calculate expiration.
- Resolve URLs.
- Reject expired URLs during redirect.
- Increment redirect counts.
- Retrieve URL details without redirecting.
- List URLs.
- Translate repository results into domain errors.
- Delete URLs.

#### `exceptions.py`

Defines meaningful application and domain failure states.

Examples:

```python
ShortUrlError
DuplicateShortCodeError
ShortCodeNotFoundError
ShortUrlExpiredError
InvalidExpirationError
ShortCodeGenerationError
```

#### `cli.py`

Acts as the presentation layer and application entry point.

Responsibilities:

- Read user input.
- Call service methods.
- Print results.
- Display domain errors.
- Keep the application running until the user exits.

Run the CLI from the project root:

```bash
python -m app.cli
```

#### `tests/`

Verifies model, repository and service behaviour independently.

### 2.3 Project Structure

```text
tiny_url/
├── app/
│   ├── __init__.py
│   ├── cli.py
│   ├── exceptions.py
│   ├── models.py
│   ├── repository.py
│   └── service.py
└── tests/
    ├── test_models.py
    ├── test_repository.py
    └── test_service.py
```

### 2.4 Application Flow

#### Create

```text
CLI input
  -> ShortUrlService.create_url()
  -> generate or accept short code
  -> create ShortUrl model
  -> ShortUrlRepository.save()
  -> return created ShortUrl
  -> CLI displays short code
```

#### Resolve

```text
CLI input
  -> ShortUrlService.resolve_url()
  -> repository.get()
  -> reject missing URL
  -> reject expired URL
  -> increment redirect count
  -> return ShortUrl
  -> CLI displays destination URL
```

#### View details

```text
CLI input
  -> ShortUrlService.get_url_details()
  -> repository.get()
  -> reject missing URL
  -> return ShortUrl without incrementing redirect count
```

#### Delete

```text
CLI input
  -> ShortUrlService.delete_url()
  -> repository.delete()
  -> repository returns True or False
  -> service raises ShortCodeNotFoundError when False
```

---

## 3. Design Decisions Made

For each significant decision, three approaches were considered:

- Naïve implementation
- Production-grade architecture
- Interview-optimised implementation

The V1 implementation generally uses the interview-optimised option.

### 3.1 Dataclass for the Domain Model

Decision:

```python
@dataclass
class ShortUrl:
    ...
```

Reasoning:

- Removes repetitive constructor and representation code.
- Makes the model clear and readable.
- Provides useful equality behaviour for tests.
- Keeps state-related behaviour close to the state itself.

Production alternative:

- Domain value objects for `ShortCode`, `DestinationUrl` and expiration.
- Immutable entities where appropriate.
- Explicit validation and richer invariants.

V1 choice:

- Use one straightforward dataclass.

### 3.2 Timezone-Aware UTC Timestamps

Decision:

```python
datetime.now(UTC)
```

Reasoning:

- Avoids ambiguous local times.
- Prevents comparison errors between naïve and timezone-aware datetimes.
- Makes tests and future persistence more reliable.

### 3.3 Injecting the Current Time

Decision:

```python
Clock = Callable[[], datetime]
```

The service accepts a clock dependency rather than directly calling the system clock in every operation.

Reasoning:

- Time-dependent tests become deterministic.
- Expiration behaviour can be tested without sleeping or patching global functions.
- The production default still uses the real UTC clock.

### 3.4 Repository as a Separate Layer

Decision:

- The service does not directly use a dictionary.
- Storage is hidden behind `ShortUrlRepository`.

Reasoning:

- Separates storage concerns from business rules.
- Makes future replacement with SQLAlchemy or another persistence mechanism easier.
- Allows repository behaviour to be tested independently.

### 3.5 Constructor-Based Dependency Injection

Decision:

```python
service = ShortUrlService(repository=repository)
```

Reasoning:

- The service does not construct its own repository.
- Tests can inject a fresh repository.
- Dependencies remain visible.
- The design is simple enough for a timed interview.

Production alternative:

- Repository protocols or abstract interfaces.
- Dependency-injection container.
- Separate infrastructure implementations.

V1 choice:

- Inject the concrete repository directly.

### 3.6 Generated Short-Code Dependency

Decision:

```python
CodeGenerator = Callable[[], str]
```

Reasoning:

- Production uses a secure random generator.
- Tests can supply predictable values such as:

```python
lambda: "abc123"
```

- Collision and retry behaviour becomes easy to test.

Production alternative:

- A dedicated `ShortCodeGenerator` interface and implementation.

V1 choice:

- Inject a callable rather than introduce another class.

### 3.7 Using `secrets` for Generated Codes

Decision:

```python
secrets.choice(...)
```

Reasoning:

- More appropriate than `random` for externally exposed identifiers.
- Reduces predictability.
- Requires little extra code.

### 3.8 Generated-Code Collision Retries

Decision:

- Attempt to save the generated code directly.
- Catch only `DuplicateShortCodeError`.
- Generate another code.
- Stop after a configured maximum number of attempts.

Reasoning:

- Avoids an unsafe check-then-act design.
- The storage layer remains the final uniqueness guarantee.
- Prevents an infinite retry loop.

Incorrect pattern avoided:

```python
if not repository.exists(code):
    repository.save(url)
```

This cannot guarantee uniqueness in concurrent systems.

### 3.9 Custom-Code Collision Behaviour

Decision:

- Do not retry when a user-supplied custom code already exists.
- Raise `DuplicateShortCodeError`.

Reasoning:

- The user explicitly requested that code.
- Silently substituting another code would violate user intent.
- This can later map to HTTP `409 Conflict`.

### 3.10 Repository Error Versus Service Error

Design principle:

```text
Repository:
    Reports storage outcomes.

Service:
    Applies business meaning.
```

For deletion, the repository returns:

```python
bool
```

The service converts `False` into:

```python
ShortCodeNotFoundError
```

Production alternative:

```text
Database exception
  -> repository-specific exception
  -> domain exception
  -> HTTP error
```

V1 choice:

- Keep error handling explicit without adding excessive exception translation layers.

### 3.11 Delete Contract

Repository contract:

```python
delete(short_code) -> bool
```

- `True`: an object existed and was deleted.
- `False`: no object existed.

Service contract:

```python
delete_url(short_code) -> None
```

- Completes normally on success.
- Raises `ShortCodeNotFoundError` on failure.

Reasoning:

- The repository provides a storage result.
- The service defines whether that result is a use-case error.
- A successful command does not need to return `True`.

### 3.12 Separate Resolve and Details Use Cases

Decision:

```python
resolve_url(short_code)
get_url_details(short_code)
```

Reasoning:

`resolve_url()`:

- Rejects expired URLs.
- Increments redirect count.

`get_url_details()`:

- Allows expired URLs.
- Does not increment redirect count.

This prevents administrative inspection from being counted as a redirect.

### 3.13 Mutating Redirect Count on the Model

Decision:

```python
short_url.record_redirect()
```

Reasoning:

- Redirect count is part of the entity's state.
- In-memory storage holds the same object reference, so the update is retained.

Production limitation:

- A database implementation should use an atomic update such as:

```sql
UPDATE short_urls
SET redirect_count = redirect_count + 1
WHERE short_code = ...
```

This avoids lost updates under concurrency.

### 3.14 Specific Exception Handling

Decision:

```python
except DuplicateShortCodeError:
    ...
```

rather than:

```python
except Exception:
    ...
```

Reasoning:

- Only known recoverable failures should be caught.
- Database failures, programming errors and unexpected exceptions must not be silently treated as collisions.

### 3.15 CLI as a Separate Presentation Layer

Decision:

- Use `app/cli.py`.
- Run using:

```bash
python -m app.cli
```

Reasoning:

- Keeps CLI concerns outside the service.
- Preserves `app/main.py` for the future FastAPI application.
- Avoids executable code being placed inside model, repository or service modules.

### 3.16 In-Memory Persistence for V1

Decision:

```python
self._urls: dict[str, ShortUrl] = {}
```

Reasoning:

- Keeps the first version focused on Python design, domain logic and testing.
- Avoids introducing database configuration before the core behaviour is understood.
- Makes the application fast to build and demonstrate.

Trade-off:

- All data disappears when the CLI process exits.

---

## 4. Mistakes Made and Lessons Learned

### 4.1 Incorrect Return for URLs Without Expiration

Initial implementation:

```python
if self.expires_at is None:
    return 0
```

Problem:

- `0` means the URL has expired or has no time remaining.
- A URL with no expiration is a different state.

Correction:

```python
if self.expires_at is None:
    return None
```

Lesson:

- Return values should preserve meaningful distinctions between domain states.

### 4.2 Expired URLs Returned Negative Remaining Seconds

Initial implementation:

```python
return int((self.expires_at - now).total_seconds())
```

Problem:

- Already-expired URLs returned negative numbers.

Correction:

```python
return max(0, seconds_remaining)
```

Lesson:

- Method contracts should define behaviour for boundary and expired states, not only the happy path.

### 4.3 Incorrect Return Type Annotation

Initial implementation:

```python
def remaining_seconds(...) -> int:
```

Problem:

- The method also needed to return `None`.

Correction:

```python
def remaining_seconds(...) -> int | None:
```

Lesson:

- Type annotations must describe every legitimate return path.

### 4.4 Delete Implementation Did Not Match the Requested Contract

Requested repository behaviour:

```text
Existing URL -> True
Missing URL  -> False
```

Initial implementation:

```python
if short_code not in self._urls:
    raise ShortCodeNotFoundError(short_code)
```

Problem:

- The implementation changed the repository contract.
- The test was named as though `False` was returned, but it expected an exception.

Correction:

```python
def delete(self, short_code: str) -> bool:
    deleted_url = self._urls.pop(short_code, None)
    return deleted_url is not None
```

Lesson:

- Method name, return type, implementation and tests must describe the same contract.

### 4.5 Test Name Contradicted Test Behaviour

Initial test name:

```python
test_delete_unknown_url_returns_false
```

Initial assertion:

```python
with pytest.raises(ShortCodeNotFoundError):
```

Problem:

- The test name documented one behaviour while the body tested another.

Lesson:

- Tests are executable documentation. Their names must precisely describe the expected behaviour.

### 4.6 Missing Exception Import in Tests

The test used:

```python
ShortCodeNotFoundError
```

but initially imported only:

```python
DuplicateShortCodeError
```

Problem:

- The test would fail with `NameError`.

Lesson:

- A test failure may come from the test itself rather than the production implementation.

### 4.7 `get_url_details()` Returned `None`

Observed CLI output:

```text
None
```

Cause:

- The method retrieved the object and handled the missing case but did not include:

```python
return short_url
```

Python automatically returns `None` when execution reaches the end of a function without an explicit return.

Lesson:

- Verify every code path against the declared return type.
- Type checking tools can detect many missing-return issues.

### 4.8 Initially Running the CLI as `app.main`

The CLI was first run using:

```bash
python -m app.main
```

It was later moved to:

```bash
python -m app.cli
```

Reason:

- `cli.py` clearly identifies the command-line presentation layer.
- `main.py` can later contain the FastAPI application object.

Lesson:

- Entry-point naming becomes important when an application supports multiple interfaces.

### 4.9 Raw Dataclass Output Is Not User-Friendly

Current listing output:

```text
ShortUrl(short_code='ex1', destination_url='...', ...)
```

This is correct but designed more for developers than CLI users.

Future improvement:

```text
Short code      : ex1
Destination URL : https://example1.com
Created at      : 2026-07-25 15:45:41 UTC
Expires at      : Never
Redirect count  : 1
```

Lesson:

- Domain representation and presentation formatting are separate concerns.

### 4.10 In-Memory Object Mutation Does Not Generalise Automatically

Current implementation:

```python
short_url.record_redirect()
```

works because the repository stores the same object reference.

Problem in a database-backed version:

- Mutating a detached object may not persist.
- Concurrent increments can overwrite one another.

Lesson:

- Behaviour that is correct for an in-memory implementation may require a different persistence strategy in production.

---

## 5. Tech Stack Used

### Language

- **Python 3**
- Modern union type syntax:

```python
datetime | None
```

### Standard Library

- `dataclasses`
  - Domain model definition.
- `datetime`
  - UTC timestamps and expiration calculation.
- `typing` / `collections.abc`
  - Callable dependency types.
- `secrets`
  - Secure short-code generation.
- `string`
  - Alphanumeric character set.

### Testing

- **pytest**
  - Unit tests.
  - Exception assertions.
  - Deterministic model, repository and service tests.

### Storage

- Python in-memory dictionary:

```python
dict[str, ShortUrl]
```

### Interface

- Interactive command-line interface using:
  - `input()`
  - `print()`
  - `python -m app.cli`

### Architecture and Patterns

- Layered architecture
- Domain model
- Repository pattern
- Service layer
- Constructor-based dependency injection
- Injected clock
- Injected code generator
- Custom domain exceptions
- Command/query separation at the use-case level
- Deterministic unit testing
- Explicit collision retry policy

### Planned Next Version

TinyURL V2 will introduce the FastAPI boundary:

- FastAPI
- Pydantic
- HTTP routes
- Dependency injection
- Domain exception to HTTP-status mapping
- Redirect responses
- API tests with `TestClient`

Potential later persistence version:

- SQLAlchemy
- SQLite or PostgreSQL
- Unique database constraints
- Transactions
- Atomic redirect-count updates
- Database migrations
