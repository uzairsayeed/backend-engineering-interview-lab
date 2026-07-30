"""HTTP routes for the quota manager."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Reservation, TenantQuota
from app.schemas import (
    ErrorResponse,
    QuotaRequest,
    QuotaResponse,
    ReservationRequest,
    ReservationResponse,
    ResourceQuantities,
)
from app.services import QuotaService, ReservationService


router = APIRouter(prefix="/tenants")
TenantId = Annotated[str, Path(min_length=1, max_length=100)]
ReservationId = Annotated[UUID, Path()]
DatabaseSession = Annotated[Session, Depends(get_db)]


def _quota_response(quota: TenantQuota) -> QuotaResponse:
    return QuotaResponse(
        tenant_id=quota.tenant_id,
        limit=ResourceQuantities(
            cpu=quota.cpu_limit,
            memory=quota.memory_limit,
            gpu=quota.gpu_limit,
        ),
        usage=ResourceQuantities(
            cpu=quota.cpu_used,
            memory=quota.memory_used,
            gpu=quota.gpu_used,
        ),
    )


def _utc(timestamp: datetime | None) -> datetime | None:
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _reservation_response(reservation: Reservation) -> ReservationResponse:
    created_at = _utc(reservation.created_at)
    if created_at is None:
        raise ValueError("Reservation creation timestamp is required")
    return ReservationResponse(
        id=reservation.id,
        tenant_id=reservation.tenant_id,
        cpu=reservation.cpu,
        memory=reservation.memory,
        gpu=reservation.gpu,
        status=reservation.status,
        created_at=created_at,
        released_at=_utc(reservation.released_at),
    )


@router.put(
    "/{tenant_id}/quota",
    tags=["quotas"],
    response_model=QuotaResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
def replace_quota(
    tenant_id: TenantId,
    payload: QuotaRequest,
    session: DatabaseSession,
) -> QuotaResponse:
    """Create or fully replace a tenant's quota."""

    quota = QuotaService(session).replace_quota(
        tenant_id,
        cpu_limit=payload.cpu,
        memory_limit=payload.memory,
        gpu_limit=payload.gpu,
    )
    return _quota_response(quota)


@router.get(
    "/{tenant_id}/quota",
    tags=["quotas"],
    response_model=QuotaResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def get_quota(tenant_id: TenantId, session: DatabaseSession) -> QuotaResponse:
    """Return a tenant's quota limits and current usage."""

    return _quota_response(QuotaService(session).get_quota(tenant_id))


@router.post(
    "/{tenant_id}/reservations",
    tags=["reservations"],
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
def create_reservation(
    tenant_id: TenantId,
    payload: ReservationRequest,
    session: DatabaseSession,
) -> ReservationResponse:
    """Create an all-or-nothing reservation."""

    reservation = ReservationService(session).create_reservation(
        tenant_id,
        cpu=payload.cpu,
        memory=payload.memory,
        gpu=payload.gpu,
    )
    return _reservation_response(reservation)


@router.get(
    "/{tenant_id}/reservations",
    tags=["reservations"],
    response_model=list[ReservationResponse],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def list_reservations(
    tenant_id: TenantId,
    session: DatabaseSession,
) -> list[ReservationResponse]:
    """List a tenant's active and released reservations."""

    reservations = ReservationService(session).list_reservations(tenant_id)
    return [_reservation_response(reservation) for reservation in reservations]


@router.get(
    "/{tenant_id}/reservations/{reservation_id}",
    tags=["reservations"],
    response_model=ReservationResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
def get_reservation(
    tenant_id: TenantId,
    reservation_id: ReservationId,
    session: DatabaseSession,
) -> ReservationResponse:
    """Retrieve one reservation scoped to its tenant."""

    reservation = ReservationService(session).get_reservation(
        tenant_id,
        str(reservation_id),
    )
    return _reservation_response(reservation)


@router.post(
    "/{tenant_id}/reservations/{reservation_id}/release",
    tags=["reservations"],
    response_model=ReservationResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
def release_reservation(
    tenant_id: TenantId,
    reservation_id: ReservationId,
    session: DatabaseSession,
) -> ReservationResponse:
    """Idempotently release a reservation."""

    reservation = ReservationService(session).release_reservation(
        tenant_id,
        str(reservation_id),
    )
    return _reservation_response(reservation)
