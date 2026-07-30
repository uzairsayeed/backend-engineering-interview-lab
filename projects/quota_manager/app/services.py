"""Business rules and transaction boundaries."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain import (
    QuotaBelowUsageError,
    QuotaExceededError,
    QuotaNotFoundError,
    ReservationNotFoundError,
)
from app.models import Reservation, TenantQuota
from app.repositories import QuotaRepository, ReservationRepository


class QuotaService:
    """Configure and retrieve tenant quotas."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.quotas = QuotaRepository(session)

    def replace_quota(
        self,
        tenant_id: str,
        *,
        cpu_limit: int,
        memory_limit: int,
        gpu_limit: int,
    ) -> TenantQuota:
        with self.session.begin():
            if self.quotas.replace_limits_if_usage_fits(
                tenant_id,
                cpu_limit=cpu_limit,
                memory_limit=memory_limit,
                gpu_limit=gpu_limit,
            ):
                quota = self.quotas.get(tenant_id)
                if quota is None:
                    raise SQLAlchemyError("Updated quota could not be reloaded")
                return quota

            quota = self.quotas.get(tenant_id)
            if quota is None:
                return self.quotas.create(
                    tenant_id,
                    cpu_limit=cpu_limit,
                    memory_limit=memory_limit,
                    gpu_limit=gpu_limit,
                )

            resources_below_usage = [
                resource
                for resource, limit, used in (
                    ("cpu", cpu_limit, quota.cpu_used),
                    ("memory", memory_limit, quota.memory_used),
                    ("gpu", gpu_limit, quota.gpu_used),
                )
                if limit < used
            ]
            if resources_below_usage:
                raise QuotaBelowUsageError(
                    details={"resources": resources_below_usage}
                )
            raise SQLAlchemyError("Quota update did not affect the expected row")

    def get_quota(self, tenant_id: str) -> TenantQuota:
        quota = self.quotas.get(tenant_id)
        if quota is None:
            raise QuotaNotFoundError()
        return quota


class ReservationService:
    """Allocate, retrieve, list, and release reservations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.quotas = QuotaRepository(session)
        self.reservations = ReservationRepository(session)

    def create_reservation(
        self,
        tenant_id: str,
        *,
        cpu: int,
        memory: int,
        gpu: int,
    ) -> Reservation:
        with self.session.begin():
            if not self.quotas.reserve_if_available(
                tenant_id,
                cpu=cpu,
                memory=memory,
                gpu=gpu,
            ):
                quota = self.quotas.get(tenant_id)
                if quota is None:
                    raise QuotaNotFoundError()

                requested = {"cpu": cpu, "memory": memory, "gpu": gpu}
                available = {
                    "cpu": quota.cpu_limit - quota.cpu_used,
                    "memory": quota.memory_limit - quota.memory_used,
                    "gpu": quota.gpu_limit - quota.gpu_used,
                }
                exceeded_resources = [
                    resource
                    for resource in requested
                    if requested[resource] > available[resource]
                ]
                raise QuotaExceededError(
                    details={
                        "resources": exceeded_resources,
                        "requested": requested,
                        "available": available,
                    }
                )

            return self.reservations.create(
                str(uuid4()),
                tenant_id,
                cpu=cpu,
                memory=memory,
                gpu=gpu,
                created_at=datetime.now(timezone.utc),
            )

    def get_reservation(
        self,
        tenant_id: str,
        reservation_id: str,
    ) -> Reservation:
        reservation = self.reservations.get(tenant_id, reservation_id)
        if reservation is None:
            raise ReservationNotFoundError()
        return reservation

    def list_reservations(self, tenant_id: str) -> list[Reservation]:
        if self.quotas.get(tenant_id) is None:
            raise QuotaNotFoundError()
        return self.reservations.list_for_tenant(tenant_id)

    def release_reservation(
        self,
        tenant_id: str,
        reservation_id: str,
    ) -> Reservation:
        with self.session.begin():
            resources = self.reservations.release_if_active(
                tenant_id,
                reservation_id,
                released_at=datetime.now(timezone.utc),
            )
            if resources is None:
                reservation = self.reservations.get(tenant_id, reservation_id)
                if reservation is None:
                    raise ReservationNotFoundError()
                return reservation

            cpu, memory, gpu = resources
            if not self.quotas.release_usage(
                tenant_id,
                cpu=cpu,
                memory=memory,
                gpu=gpu,
            ):
                raise SQLAlchemyError(
                    "Reservation usage could not be released safely"
                )

            reservation = self.reservations.get(tenant_id, reservation_id)
            if reservation is None:
                raise SQLAlchemyError("Released reservation could not be reloaded")
            return reservation
