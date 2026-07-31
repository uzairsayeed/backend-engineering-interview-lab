"""Public API request, stream, and error schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MessageRole = Literal["system", "user", "assistant"]
ErrorCode = Literal[
    "validation_error",
    "upstream_error",
    "invalid_upstream_response",
    "all_providers_failed",
    "internal_error",
]


class StrictSchema(BaseModel):
    """Base schema that rejects fields outside the public contract."""

    model_config = ConfigDict(extra="forbid")


class ChatMessage(StrictSchema):
    """One text message in a chat completion request."""

    role: MessageRole
    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message content must not be empty.")
        return value


class ChatCompletionRequest(StrictSchema):
    """The supported streaming-only chat completion request."""

    model: Literal["general-chat"]
    messages: list[ChatMessage] = Field(min_length=1)
    stream: Literal[True]


class ContentDelta(StrictSchema):
    """The text added by one normalized stream event."""

    content: str


class StreamChoice(StrictSchema):
    """The single choice supported by this gateway."""

    index: Literal[0] = 0
    delta: ContentDelta


class ContentDeltaChunk(StrictSchema):
    """A provider-independent client-visible stream payload."""

    choices: list[StreamChoice] = Field(min_length=1, max_length=1)


class ValidationErrorDetail(StrictSchema):
    """One Pydantic validation error exposed by the API."""

    loc: list[str | int]
    msg: str
    type: str


class ErrorBody(StrictSchema):
    """Machine-readable and sanitized gateway error information."""

    code: ErrorCode
    message: str
    details: list[ValidationErrorDetail] | None = None


class ErrorResponse(StrictSchema):
    """Public JSON error envelope."""

    error: ErrorBody
