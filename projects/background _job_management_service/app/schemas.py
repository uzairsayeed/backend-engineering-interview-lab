from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain import JobStatus


class JobCreate(BaseModel):
    duration_seconds: Annotated[int, Field(ge=1, le=10)]
    should_fail: bool


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    duration_seconds: int
    should_fail: bool
    status: JobStatus
    retry_count: int
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    @field_serializer(
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        when_used="json",
    )
    def serialize_utc_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
