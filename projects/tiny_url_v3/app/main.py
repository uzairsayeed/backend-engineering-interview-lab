# FastAPI application
# │
# ├── One application-level Engine
# │
# ├── Per request
# │   ├── Session
# │   ├── SQLShortUrlRepository
# │   └── ShortUrlService
# │
# ├── Success
# │   └── Commit
# │
# ├── Failure
# │   └── Rollback
# │
# └── Request complete
#     └── Close Session

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import (
    check_database_connection,
    dispose_database,
)
from app.exception_handlers import (
    register_exception_handlers,
)
from app.logging_config import configure_logging
from app.routers import redirects, urls
from app.schemas import HealthResponse

settings = get_settings()

configure_logging(settings.log_level)

logger = logging.getLogger("tinyurl.main")

# Application lifecycle:
    # Start process
    # ↓
    # Run code before yield
    #     ↓
    # Accept and process requests
    #     ↓
    # Application stops
    #     ↓
    # Run code after yield

# Database lifecycle:
    # Startup
    #     ↓
    # Check connectivity
    #     ↓
    # Create missing tables
    #     ↓
    # Serve requests
    #     ↓
    # Dispose database pool
    #     ↓
    # Shutdown

@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    del app

    check_database_connection()

    logger.info(
        "application_started "
        "name=%s version=%s "
        "public_base_url=%s "
        "database_configured=true",
        settings.app_name,
        settings.app_version,
        settings.public_base_url,
    )

    yield

    dispose_database()

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
