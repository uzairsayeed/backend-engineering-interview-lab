"""FastAPI route and public response formatting."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from app.errors import GatewayError, InternalGatewayError
from app.providers.base import ContentEvent, DoneEvent
from app.schemas import (
    ChatCompletionRequest,
    ContentDelta,
    ContentDeltaChunk,
    ErrorBody,
    ErrorResponse,
    StreamChoice,
    ValidationErrorDetail,
)
from app.service import ChatCompletionService, PreparedStream

router = APIRouter()


def get_chat_completion_service(request: Request) -> ChatCompletionService:
    """Retrieve the application-owned chat-completion service."""

    return request.app.state.chat_completion_service


ServiceDependency = Annotated[
    ChatCompletionService,
    Depends(get_chat_completion_service),
]


async def encode_sse(stream: PreparedStream) -> AsyncIterator[str]:
    """Translate normalized internal events into the public SSE contract."""

    async for event in stream:
        if isinstance(event, ContentEvent):
            chunk = ContentDeltaChunk(
                choices=[
                    StreamChoice(
                        delta=ContentDelta(content=event.content)
                    )
                ]
            )
            yield f"data: {chunk.model_dump_json()}\n\n"
        elif isinstance(event, DoneEvent):
            yield "data: [DONE]\n\n"
            return


@router.get("/health")
async def health() -> dict[str, str]:
    """Report process health without contacting upstream providers."""

    return {"status": "ok"}


@router.post("/v1/chat/completions")
async def create_chat_completion(
    payload: ChatCompletionRequest,
    service: ServiceDependency,
) -> StreamingResponse:
    """Create a streaming chat completion."""

    stream = await service.prepare_stream(payload)
    return StreamingResponse(
        encode_sse(stream),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def gateway_error_handler(
    request: Request, exception: GatewayError
) -> JSONResponse:
    """Convert a known pre-stream gateway error to the public envelope."""

    response = ErrorResponse(
        error=ErrorBody(
            code=exception.code,
            message=exception.message,
        )
    )
    return JSONResponse(
        status_code=exception.status_code,
        content=response.model_dump(exclude_none=True),
    )


async def validation_error_handler(
    request: Request, exception: RequestValidationError
) -> JSONResponse:
    """Normalize FastAPI/Pydantic request validation errors."""

    details = [
        ValidationErrorDetail(
            loc=list(error["loc"]),
            msg=error["msg"],
            type=error["type"],
        )
        for error in exception.errors()
    ]
    response = ErrorResponse(
        error=ErrorBody(
            code="validation_error",
            message="Request validation failed.",
            details=details,
        )
    )
    return JSONResponse(
        status_code=422,
        content=response.model_dump(exclude_none=True),
    )


async def internal_error_handler(
    request: Request, exception: Exception
) -> JSONResponse:
    """Return a sanitized response for an unexpected pre-stream failure."""

    error = InternalGatewayError()
    response = ErrorResponse(
        error=ErrorBody(code=error.code, message=error.message)
    )
    return JSONResponse(
        status_code=error.status_code,
        content=response.model_dump(exclude_none=True),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the public error mappings on the application."""

    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(GatewayError, gateway_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
