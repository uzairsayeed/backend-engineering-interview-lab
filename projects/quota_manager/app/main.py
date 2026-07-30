"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.database import engine
from app.domain import (
    DomainError,
    QuotaBelowUsageError,
    QuotaExceededError,
    QuotaNotFoundError,
    ReservationNotFoundError,
)
from app.routes import router
from app.schemas import ErrorDetail, ErrorResponse


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Verify startup readiness and release database resources on shutdown."""

    logger.info(
        "Starting %s version %s",
        application.title,
        application.version,
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        yield
    finally:
        engine.dispose()
        logger.info("Application stopped")


app = FastAPI(
    title="Multi-Tenant Cloud Resource Quota Manager",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)

DOMAIN_ERROR_STATUSES: dict[type[DomainError], int] = {
    QuotaNotFoundError: status.HTTP_404_NOT_FOUND,
    ReservationNotFoundError: status.HTTP_404_NOT_FOUND,
    QuotaBelowUsageError: status.HTTP_409_CONFLICT,
    QuotaExceededError: status.HTTP_409_CONFLICT,
}


def _error_content(
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    response = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details)
    )
    return response.model_dump()


@app.exception_handler(DomainError)
def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
    """Translate business errors into stable HTTP responses."""

    return JSONResponse(
        status_code=DOMAIN_ERROR_STATUSES.get(type(exc), status.HTTP_400_BAD_REQUEST),
        content=_error_content(exc.code, exc.message, exc.details),
    )


@app.exception_handler(SQLAlchemyError)
def handle_database_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Hide database internals while preserving the exception in logs."""

    logger.error(
        "Database operation failed",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_content(
            "DATABASE_ERROR",
            "A database operation failed",
        ),
    )


@app.exception_handler(RequestValidationError)
def handle_validation_error(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return Pydantic validation failures in the common error envelope."""

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_content(
            "VALIDATION_ERROR",
            "Request validation failed",
            {"errors": jsonable_encoder(exc.errors())},
        ),
    )


@app.exception_handler(HTTPException)
def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
    """Keep framework-generated HTTP errors consistent with domain errors."""

    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details = None if isinstance(exc.detail, str) else {"detail": exc.detail}
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_content("HTTP_ERROR", message, details),
        headers=exc.headers,
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Report whether the API process is running."""

    return {"status": "ok"}
