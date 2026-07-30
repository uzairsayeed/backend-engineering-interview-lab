"""Database access operations without transaction ownership."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain import ReservationStatus
from app.models import Reservation, TenantQuota


class QuotaRepository:
    """Persistence operations for tenant quotas."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, tenant_id: str) -> TenantQuota | None:
        return self.session.get(TenantQuota, tenant_id)

    def create(
        self,
        tenant_id: str,
        *,
        cpu_limit: int,
        memory_limit: int,
        gpu_limit: int,
    ) -> TenantQuota:
        quota = TenantQuota(
            tenant_id=tenant_id,
            cpu_limit=cpu_limit,
            memory_limit=memory_limit,
            gpu_limit=gpu_limit,
        )
        self.session.add(quota)
        self.session.flush()
        return quota

    def replace_limits_if_usage_fits(
        self,
        tenant_id: str,
        *,
        cpu_limit: int,
        memory_limit: int,
        gpu_limit: int,
    ) -> bool:
        statement = (
            update(TenantQuota)
            .where(
                TenantQuota.tenant_id == tenant_id,
                TenantQuota.cpu_used <= cpu_limit,
                TenantQuota.memory_used <= memory_limit,
                TenantQuota.gpu_used <= gpu_limit,
            )
            .values(
                cpu_limit=cpu_limit,
                memory_limit=memory_limit,
                gpu_limit=gpu_limit,
            )
        )
        result = self.session.execute(statement)
        return result.rowcount == 1

    def reserve_if_available(
        self,
        tenant_id: str,
        *,
        cpu: int,
        memory: int,
        gpu: int,
    ) -> bool:
        statement = (
            update(TenantQuota)
            .where(
                TenantQuota.tenant_id == tenant_id,
                TenantQuota.cpu_used + cpu <= TenantQuota.cpu_limit,
                TenantQuota.memory_used + memory <= TenantQuota.memory_limit,
                TenantQuota.gpu_used + gpu <= TenantQuota.gpu_limit,
            )
            .values(
                cpu_used=TenantQuota.cpu_used + cpu,
                memory_used=TenantQuota.memory_used + memory,
                gpu_used=TenantQuota.gpu_used + gpu,
            )
        )
        result = self.session.execute(statement)
        return result.rowcount == 1

    def release_usage(
        self,
        tenant_id: str,
        *,
        cpu: int,
        memory: int,
        gpu: int,
    ) -> bool:
        statement = (
            update(TenantQuota)
            .where(
                TenantQuota.tenant_id == tenant_id,
                TenantQuota.cpu_used >= cpu,
                TenantQuota.memory_used >= memory,
                TenantQuota.gpu_used >= gpu,
            )
            .values(
                cpu_used=TenantQuota.cpu_used - cpu,
                memory_used=TenantQuota.memory_used - memory,
                gpu_used=TenantQuota.gpu_used - gpu,
            )
        )
        result = self.session.execute(statement)
        return result.rowcount == 1


class ReservationRepository:
    """Persistence operations for tenant-scoped reservations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        reservation_id: str,
        tenant_id: str,
        *,
        cpu: int,
        memory: int,
        gpu: int,
        created_at: datetime,
    ) -> Reservation:
        reservation = Reservation(
            id=reservation_id,
            tenant_id=tenant_id,
            cpu=cpu,
            memory=memory,
            gpu=gpu,
            status=ReservationStatus.ACTIVE,
            created_at=created_at,
        )
        self.session.add(reservation)
        self.session.flush()
        return reservation

    def get(self, tenant_id: str, reservation_id: str) -> Reservation | None:
        statement = select(Reservation).where(
            Reservation.tenant_id == tenant_id,
            Reservation.id == reservation_id,
        )
        return self.session.scalar(statement)

    def list_for_tenant(self, tenant_id: str) -> list[Reservation]:
        statement = (
            select(Reservation)
            .where(Reservation.tenant_id == tenant_id)
            .order_by(Reservation.created_at, Reservation.id)
        )
        return list(self.session.scalars(statement))

    def release_if_active(
        self,
        tenant_id: str,
        reservation_id: str,
        *,
        released_at: datetime,
    ) -> tuple[int, int, int] | None:
        statement = (
            update(Reservation)
            .where(
                Reservation.tenant_id == tenant_id,
                Reservation.id == reservation_id,
                Reservation.status == ReservationStatus.ACTIVE,
            )
            .values(
                status=ReservationStatus.RELEASED,
                released_at=released_at,
            )
            .returning(Reservation.cpu, Reservation.memory, Reservation.gpu)
        )
        row = self.session.execute(statement).first()
        if row is None:
            return None
        return row.cpu, row.memory, row.gpu
