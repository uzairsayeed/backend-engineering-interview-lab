import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import (
    HTTPException as StarletteHTTPException,
)

from app.exceptions import (
    DuplicateShortCodeError,
    InvalidExpirationError,
    ReservedShortCodeError,
    ShortCodeGenerationError,
    ShortCodeNotFoundError,
    ShortUrlError,
    ShortUrlExpiredError,
)
from app.schemas import (
    ErrorDetail,
    ErrorResponse,
    ValidationIssue,
)

logger = logging.getLogger("tinyurl.errors")

ErrorConfig = tuple[int, str]


ERROR_CONFIG: dict[type[ShortUrlError], ErrorConfig] = {
    DuplicateShortCodeError: (
        status.HTTP_409_CONFLICT,
        "duplicate_short_code",
    ),
    ReservedShortCodeError: (
        status.HTTP_409_CONFLICT,
        "reserved_short_code",
    ),
    ShortCodeNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "short_code_not_found",
    ),
    ShortUrlExpiredError: (
        status.HTTP_410_GONE,
        "short_url_expired",
    ),
    InvalidExpirationError: (
        status.HTTP_400_BAD_REQUEST,
        "invalid_expiration",
    ),
    ShortCodeGenerationError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "short_code_generation_failed",
    ),
}


def build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[ValidationIssue] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    response_body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
        )
    )

    return JSONResponse(
        status_code=status_code,
        content=response_body.model_dump(
            mode="json",
            exclude_none=True,
        ),
        headers=headers,
    )


def format_error_location(
    location: Sequence[Any],
) -> str:
    return ".".join(str(part) for part in location)


async def handle_short_url_error(
    request: Request,
    error: ShortUrlError,
) -> JSONResponse:
    del request

    status_code, error_code = ERROR_CONFIG.get(
        type(error),
        (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "short_url_error",
        ),
    )

    return build_error_response(
        status_code=status_code,
        code=error_code,
        message=str(error),
    )


async def handle_request_validation_error(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    del request

    issues = [
        ValidationIssue(
            location=format_error_location(validation_error["loc"]),
            message=validation_error["msg"],
            type=validation_error["type"],
        )
        for validation_error in error.errors()
    ]

    return build_error_response(
        status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
        code="request_validation_failed",
        message="Request validation failed",
        details=issues,
    )


async def handle_http_exception(
    request: Request,
    error: StarletteHTTPException,
) -> JSONResponse:
    del request

    error_codes = {
        status.HTTP_404_NOT_FOUND: "route_not_found",
        status.HTTP_405_METHOD_NOT_ALLOWED: ("method_not_allowed"),
    }

    error_code = error_codes.get(
        error.status_code,
        "http_error",
    )

    return build_error_response(
        status_code=error.status_code,
        code=error_code,
        message=str(error.detail),
        headers=error.headers,
    )


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
        status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
        code="internal_server_error",
        message="An unexpected error occurred",
    )


def register_exception_handlers(
    app: FastAPI,
) -> None:
    app.add_exception_handler(
        ShortUrlError,
        handle_short_url_error,
    )

    app.add_exception_handler(
        RequestValidationError,
        handle_request_validation_error,
    )

    app.add_exception_handler(
        StarletteHTTPException,
        handle_http_exception,
    )

    app.add_exception_handler(
        Exception,
        handle_unexpected_error,
    )
