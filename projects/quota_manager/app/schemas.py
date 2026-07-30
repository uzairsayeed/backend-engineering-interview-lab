"""Pydantic contracts exposed by the HTTP API."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.domain import ReservationStatus


NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]


class ResourceQuantities(BaseModel):
    """CPU millicores, memory MiB, and whole GPU quantities."""

    cpu: NonNegativeInt
    memory: NonNegativeInt
    gpu: NonNegativeInt


class QuotaRequest(ResourceQuantities):
    """Complete replacement limits for a tenant quota."""


class QuotaResponse(BaseModel):
    """A tenant's configured limits and current usage."""

    tenant_id: str
    limit: ResourceQuantities
    usage: ResourceQuantities


class ReservationRequest(ResourceQuantities):
    """All-or-nothing resources requested by a tenant."""


class ReservationResponse(BaseModel):
    """Persisted reservation state."""

    id: str
    tenant_id: str
    cpu: int
    memory: int
    gpu: int
    status: ReservationStatus
    created_at: datetime
    released_at: datetime | None


class ErrorDetail(BaseModel):
    """Stable machine-readable and human-readable error information."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Consistent envelope for API errors."""

    error: ErrorDetail
