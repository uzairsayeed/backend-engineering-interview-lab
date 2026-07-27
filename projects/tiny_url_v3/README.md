# 🔗 TinyURL API V3

> A persistent, typed URL-shortening API built with FastAPI and SQLAlchemy.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](#tests-and-quality)
[![Style](https://img.shields.io/badge/style-Ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)

Create short links, choose custom aliases, add expiration times, and track
redirects. V3 stores links in a relational database and manages schema changes
with Alembic, so data survives application restarts.

**Quick links:** [Get started](#-quick-start) ·
[Try the API](#-try-it) · [Endpoints](#-api-reference) ·
[Configuration](#-configuration) · [Architecture](#-architecture)

## ✨ Features

- Generated short codes and custom aliases
- Optional expiration from one second to one year
- `307 Temporary Redirect` responses with redirect counting
- URL metadata retrieval, listing, and deletion
- Reserved-alias and duplicate-alias protection
- Typed validation and consistent JSON error responses
- Environment-based configuration and structured logging
- SQLAlchemy persistence with per-request sessions and transactions
- Alembic database migrations
- Unit, API, and database integration tests

## 🚀 Quick start

### 1. Install

```bash
git clone <repository-url>
cd tiny_url_v3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

### 2. Prepare the database

Apply all versioned migrations to the configured database:

```bash
python -m alembic upgrade head
```

The default configuration creates `tinyurl.db` in the project directory.

### 3. Run

```bash
python -m uvicorn app.main:app --reload
```

### 4. Explore

Once the server is running:

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **OpenAPI JSON:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

## 🧪 Try it

<details open>
<summary><strong>Create a short URL</strong></summary>

```bash
curl --request POST http://127.0.0.1:8000/urls \
  --header "Content-Type: application/json" \
  --data '{
    "destination_url": "https://example.com/articles/python",
    "custom_code": "python",
    "expires_in_seconds": 3600
  }'
```

Example response:

```json
{
  "short_code": "python",
  "destination_url": "https://example.com/articles/python",
  "short_url": "http://127.0.0.1:8000/python",
  "created_at": "2026-07-26T10:00:00Z",
  "expires_at": "2026-07-26T11:00:00Z",
  "redirect_count": 0
}
```

</details>

<details>
<summary><strong>Follow the redirect</strong></summary>

```bash
curl --location --include http://127.0.0.1:8000/python
```

The API returns a `307 Temporary Redirect` and sets `Cache-Control: no-store`.

</details>

<details>
<summary><strong>Inspect, list, and delete links</strong></summary>

```bash
# Retrieve metadata
curl http://127.0.0.1:8000/urls/python

# List every short URL
curl http://127.0.0.1:8000/urls

# Delete a short URL
curl --request DELETE --include http://127.0.0.1:8000/urls/python
```

</details>

## 📚 API reference

| Method | Endpoint | Success | Purpose |
|:--|:--|:--:|:--|
| `GET` | `/health` | `200` | Check API health |
| `POST` | `/urls` | `201` | Create a short URL |
| `GET` | `/urls` | `200` | List short URLs |
| `GET` | `/urls/{short_code}` | `200` | Retrieve URL metadata |
| `DELETE` | `/urls/{short_code}` | `204` | Delete a short URL |
| `GET` | `/{short_code}` | `307` | Redirect to its destination |

<details>
<summary><strong>Request rules</strong></summary>

- `destination_url` must be an HTTP or HTTPS URL.
- `custom_code` is optional and must contain 3–32 letters, numbers,
  underscores, or hyphens.
- `expires_in_seconds` is optional and must be between `1` and `31,536,000`.
- Reserved codes are `health`, `urls`, `docs`, `redoc`, and `openapi.json`.
- Unknown, expired, conflicting, and invalid requests use structured error
  responses.

</details>

<details>
<summary><strong>Error response shape</strong></summary>

```json
{
  "error": {
    "code": "short_code_not_found",
    "message": "Short code 'missing' was not found",
    "details": null
  }
}
```

</details>

## ⚙️ Configuration

Copy `.env.example` to `.env`, then customize any of these values:

| Variable | Default | Description |
|:--|:--|:--|
| `TINYURL_APP_NAME` | `TinyURL API` | Name shown in API documentation |
| `TINYURL_APP_VERSION` | `3.0.0` | Reported application version |
| `TINYURL_PUBLIC_BASE_URL` | `http://127.0.0.1:8000` | Base URL for generated links |
| `TINYURL_LOG_LEVEL` | `INFO` | Application logging level |
| `TINYURL_DATABASE_URL` | `sqlite:///./tinyurl.db` | SQLAlchemy database connection URL |
| `TINYURL_DATABASE_ECHO` | `false` | Log generated SQL statements |

The application and Alembic both read `TINYURL_DATABASE_URL`, ensuring runtime
queries and migrations target the same database.

### Database migrations

```bash
# Apply all pending migrations
python -m alembic upgrade head

# Show the current database revision
python -m alembic current

# Roll back one migration
python -m alembic downgrade -1
```

After changing an ORM model, generate a candidate migration and review it before
applying it:

```bash
python -m alembic revision --autogenerate -m "describe schema change"
python -m alembic upgrade head
```

## 🏗️ Architecture

```text
HTTP Client
    ↓
FastAPI Router
    ↓
Pydantic Request Validation
    ↓
ShortUrlService
    ↓
ShortUrlRepositoryProtocol
    ↓
SQLShortUrlRepository
    ↓
SQLAlchemy Session
    ↓
SQLAlchemy Engine
    ↓
SQLite Database
```

Each request receives its own SQLAlchemy session, repository, and service.
Successful requests commit before the response is sent; failed requests roll
back. Repository methods flush changes but leave transaction ownership to the
request dependency. Redirect counters use a database-side atomic increment.

<details>
<summary><strong>Project structure</strong></summary>

```text
tiny_url_v3/
├── app/
│   ├── routers/               # URL and redirect endpoints
│   ├── config.py              # Environment settings
│   ├── database.py            # Engine and session factory
│   ├── database_models.py     # SQLAlchemy ORM models
│   ├── dependencies.py        # Dependency wiring
│   ├── exception_handlers.py  # HTTP error translation
│   ├── models.py              # Domain model
│   ├── persistence_mappers.py # Domain/ORM conversion
│   ├── repository.py          # In-memory test implementation
│   ├── repository_protocol.py # Service persistence contract
│   ├── schemas.py             # Request and response models
│   ├── service.py             # Business logic
│   ├── sql_repository.py      # SQLAlchemy repository
│   └── main.py                # FastAPI application
├── migrations/
│   ├── versions/              # Versioned schema migrations
│   └── env.py                 # Alembic application integration
├── tests/
│   ├── api/                   # Endpoint tests
│   ├── integration/           # Database integration tests
│   └── test_*.py              # Unit tests
├── .env.example
├── alembic.ini
├── pyproject.toml
└── README.md
```

</details>

## ✅ Tests and quality

```bash
# Run all tests
python -m pytest

# Run only database integration tests
python -m pytest tests/integration

# Check lint rules
python -m ruff check .

# Check formatting without changing files
python -m ruff format --check .

# Apply formatting
python -m ruff format .
```

## ⚠️ Current limitations

- SQLite is the default and is intended for local or learning use; production
  deployments should use an appropriately configured database.
- Authentication, authorization, URL ownership, rate limiting, and list
  pagination are not implemented.
- Expired links remain stored until explicitly deleted.
- A single public short-link domain is supported.
