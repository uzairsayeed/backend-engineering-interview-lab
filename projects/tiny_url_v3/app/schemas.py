from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
)

from app.constants import (
    SHORT_CODE_MAX_LENGTH,
    SHORT_CODE_MIN_LENGTH,
    SHORT_CODE_PATTERN,
)


ShortCode = Annotated[
    str,
    Field(
        min_length=SHORT_CODE_MIN_LENGTH,
        max_length=SHORT_CODE_MAX_LENGTH,
        pattern=SHORT_CODE_PATTERN,
        description=(
            "Custom short code containing letters, numbers, underscores or hyphens."
        ),
        examples=["python-guide"],
    ),
]


class CreateShortUrlRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    destination_url: HttpUrl = Field(
        description="The URL that the short link redirects to.",
        examples=["https://example.com/articles/python"],
    )

    custom_code: ShortCode | None = None

    expires_in_seconds: int | None = Field(
        default=None,
        gt=0,
        le=31_536_000,
        description=(
            "Number of seconds before the short URL expires. The maximum is one year."
        ),
        examples=[3600],
    )


class ShortUrlResponse(BaseModel):
    short_code: str
    destination_url: str
    short_url: str
    created_at: datetime
    expires_at: datetime | None
    redirect_count: int


class HealthResponse(BaseModel):
    status: str


class ValidationIssue(BaseModel):
    location: str
    message: str
    type: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[ValidationIssue] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
