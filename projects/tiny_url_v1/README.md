# 🔗 TinyURL — V1

A plain-Python, in-memory URL shortener built from scratch with a clean layered architecture and an interactive CLI. This is **V1** of a multi-version project — built intentionally without frameworks to focus on Python design, domain modelling, and testability.

---

## ✨ What It Does

| Feature | Description |
|---|---|
| **Create** | Shorten any URL with an auto-generated or custom short code |
| **Resolve** | Look up a short code and get redirected to the destination |
| **View Details** | Inspect a URL's metadata without counting it as a redirect |
| **List** | See all stored short URLs |
| **Delete** | Remove a short URL by its code |
| **Expiration** | Optionally set a TTL — expired URLs are rejected on resolve |

---

## 🚀 Quick Start

```bash
# Clone and enter the project
git clone <your-repo-url>
cd tiny_url

# Create a virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the CLI
python -m app.cli
```

**Example session:**

```
1. Create short URL
2. Resolve short URL
3. View URL details
4. List URLs
5. Delete URL
6. Exit

Choose an option: 1
Destination URL: https://github.com
Custom code, or leave blank: gh

Created short code: gh
```

---

## 🏗️ Architecture

```
Interactive CLI
      │
      ▼
ShortUrlService       ← business rules & use cases
      │
      ▼
ShortUrlRepository    ← storage (in-memory dict)
      │
      ▼
ShortUrl model        ← domain object
```

Each layer has a single, clear responsibility. The layers only communicate downward.

---

## 📁 Project Structure

```
tiny_url/
├── app/
│   ├── cli.py            # Presentation layer & entry point
│   ├── service.py        # Application use cases
│   ├── repository.py     # Storage operations
│   ├── models.py         # ShortUrl domain model
│   └── exceptions.py     # Domain exceptions
└── tests/
    ├── test_models.py
    ├── test_repository.py
    └── test_service.py
```

---

## 🧩 Layer Responsibilities

### `models.py` — Domain Model
Defines what a `ShortUrl` is and what it knows about itself.
```python
@dataclass
class ShortUrl:
    short_code: str
    destination_url: str
    created_at: datetime
    expires_at: datetime | None
    redirect_count: int

    def is_expired() -> bool
    def record_redirect() -> None
    def remaining_seconds() -> int | None
```

### `repository.py` — Storage
Hides all storage logic behind a clean interface. Currently uses an in-memory dict.
```python
repo.save(short_url)
repo.get(short_code)       # returns None if not found
repo.exists(short_code)
repo.list_all()
repo.delete(short_code)    # returns True/False
```

### `service.py` — Business Rules
Orchestrates use cases. Decides what's valid, what errors mean, and what callers get back.
```python
service.create_url(destination_url, custom_code, expires_in_seconds)
service.resolve_url(short_code)       # increments redirect count
service.get_url_details(short_code)   # does NOT increment redirect count
service.list_urls()
service.delete_url(short_code)
```

### `exceptions.py` — Domain Errors
```python
ShortUrlError               # base class
DuplicateShortCodeError
ShortCodeNotFoundError
ShortUrlExpiredError
InvalidExpirationError
ShortCodeGenerationError
```

---

## 🔑 Key Design Decisions

<details>
<summary><strong>Dependency injection for testability</strong></summary>

The service accepts its dependencies — never creates them:
```python
service = ShortUrlService(repository=repository)
```
Tests inject a fresh repository. Dependencies stay visible.

</details>

<details>
<summary><strong>Injected clock for deterministic time tests</strong></summary>

```python
Clock = Callable[[], datetime]
```
Instead of calling `datetime.now()` directly, the service accepts a clock. Tests can freeze time without patching globals.

</details>

<details>
<summary><strong>Injected code generator for collision testing</strong></summary>

```python
CodeGenerator = Callable[[], str]
```
Production uses `secrets.choice()`. Tests supply:
```python
lambda: "abc123"
```
This makes collision and retry logic fully testable.

</details>

<details>
<summary><strong>Collision retry — safe check-then-act avoided</strong></summary>

The service attempts to save directly and catches `DuplicateShortCodeError` rather than checking first:
```python
# ❌ Unsafe — race condition possible
if not repo.exists(code):
    repo.save(url)

# ✅ Safe — storage is the uniqueness guarantee
try:
    repo.save(url)
except DuplicateShortCodeError:
    # retry
```

</details>

<details>
<summary><strong>Resolve vs View Details — command/query separation</strong></summary>

| Method | Rejects expired? | Increments count? |
|---|---|---|
| `resolve_url()` | ✅ Yes | ✅ Yes |
| `get_url_details()` | ❌ No | ❌ No |

Admin inspection should never be counted as a redirect.

</details>

<details>
<summary><strong>Repository returns bool, service raises exception</strong></summary>

```python
# repository.delete() → bool (storage result)
# service.delete_url() → None, raises ShortCodeNotFoundError if False
```
The repository reports storage outcomes. The service decides what those outcomes mean for the application.

</details>

---

## 🧪 Running Tests

```bash
pytest
```

Tests cover:
- Model expiration, redirect counting, and edge cases
- Repository save/get/delete/collision contracts
- Service use cases including error paths, collision retries, and clock-based expiration

---

## 🛠️ Tech Stack

| Concern | Tool |
|---|---|
| Language | Python 3 (modern `X \| Y` union syntax) |
| Domain model | `dataclasses` |
| Timestamps | `datetime` with UTC (timezone-aware) |
| Code generation | `secrets` (cryptographically appropriate) |
| Dependency types | `Callable` from `typing` |
| Testing | `pytest` |
| Storage | In-memory `dict[str, ShortUrl]` |
| Interface | Interactive CLI (`input` / `print`) |

---

## ⚠️ V1 Limitations

- Data lives only in memory — everything is lost when the process exits
- No URL format validation (deferred to FastAPI/Pydantic in V2)
- No authentication, rate limiting, or analytics
- Redirect count mutation is not atomic (safe for single-process only)

---

## 🗺️ What's Next — V2 Preview

V2 will introduce the HTTP layer:

- **FastAPI** — routes and dependency injection
- **Pydantic** — request/response validation
- **HTTP semantics** — `302 Redirect`, `404`, `409 Conflict`, `410 Gone`
- **TestClient** — API-level tests
- Planned later: SQLAlchemy + SQLite/PostgreSQL with atomic redirect-count updates

---

## 📖 Lessons Learned

A few bugs caught during development worth noting:

- **Return `None`, not `0`** for URLs with no expiration — `0` means expired, `None` means "never expires". Different states deserve different values.
- **`max(0, seconds)`** — expired URLs should return `0` remaining seconds, never a negative number.
- **Tests are documentation** — a test named `test_delete_unknown_url_returns_false` that asserts `pytest.raises(...)` is lying. Name and behaviour must match.
- **Every code path needs a `return`** — Python silently returns `None` at the end of a function. Type annotations and type checkers catch this.
- **Catch specific exceptions** — `except DuplicateShortCodeError` not `except Exception`. Swallowing unknown errors hides real bugs.

---

*Built as part of a back-on-track learning project. V1 is intentionally framework-free to focus on core Python design before adding FastAPI, Pydantic, and a database in V2.*
