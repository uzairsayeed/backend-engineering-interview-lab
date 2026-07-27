from typing import Any

from fastapi import status

from app.schemas import ErrorResponse

VALIDATION_ERROR_RESPONSE: dict[int, dict[str, Any]] = {
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "model": ErrorResponse,
        "description": "Request validation failed.",
    }
}
