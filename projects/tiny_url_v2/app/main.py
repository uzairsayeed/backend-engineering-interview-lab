# main.py
#   │
#   ├── app = FastAPI(...)              ← creates the app
#   │
#   ├── register_exception_handlers(app)
#   │     └── exception_handlers.py    ← maps exceptions → HTTP error responses
#   │           └── app.exceptions     ← your custom exception classes
#   │
#   ├── app.include_router(urls.router)
#   │     └── routers/urls.py          ← POST /urls route
#   │           ├── dependencies.py    ← injects ShortUrlService
#   │           │     ├── repository.py
#   │           │     └── service.py
#   │           ├── schemas.py         ← request/response shapes
#   │           └── mappers.py         ← model → response converter
#   │
#   └── GET /health                    ← defined directly in main.py


import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.dependencies import get_settings
from app.exception_handlers import (
    register_exception_handlers,
)
from app.logging_config import configure_logging
from app.routers import redirects, urls
from app.schemas import HealthResponse

settings = get_settings()

configure_logging(settings.log_level)

logger = logging.getLogger("tinyurl.main")

# Start process
# ↓
# Run code before yield
#     ↓
# Accept and process requests
#     ↓
# Application stops
#     ↓
# Run code after yield


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    del app

    logger.info(
        "application_started name=%s version=%s public_base_url=%s",
        settings.app_name,
        settings.app_version,
        settings.public_base_url,
    )

    yield

    logger.info("application_stopped")


app = FastAPI(
    title=settings.app_name,
    description=("HTTP API for creating and resolving short URLs."),
    version=settings.app_version,
    lifespan=lifespan,
)

register_exception_handlers(app)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Check application health",
)
def health_check() -> HealthResponse:
    return HealthResponse(status="healthy")


app.include_router(urls.router)
app.include_router(redirects.router)
