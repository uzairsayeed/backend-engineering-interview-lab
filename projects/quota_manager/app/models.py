"""SQLAlchemy persistence models."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.domain import ReservationStatus


class TenantQuota(Base):
    """Configured resource limits and current usage for one tenant."""

    __tablename__ = "tenant_quotas"
    __table_args__ = (
        CheckConstraint("length(tenant_id) > 0", name="ck_tenant_quotas_tenant_id"),
        CheckConstraint(
            "cpu_limit >= 0 AND memory_limit >= 0 AND gpu_limit >= 0",
            name="ck_tenant_quotas_non_negative_limits",
        ),
        CheckConstraint(
            "cpu_used >= 0 AND memory_used >= 0 AND gpu_used >= 0",
            name="ck_tenant_quotas_non_negative_usage",
        ),
        CheckConstraint(
            "cpu_used <= cpu_limit "
            "AND memory_used <= memory_limit "
            "AND gpu_used <= gpu_limit",
            name="ck_tenant_quotas_usage_within_limits",
        ),
    )

    tenant_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    cpu_limit: Mapped[int] = mapped_column(Integer)
    memory_limit: Mapped[int] = mapped_column(Integer)
    gpu_limit: Mapped[int] = mapped_column(Integer)
    cpu_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    memory_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    gpu_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Reservation(Base):
    """An all-or-nothing allocation belonging to one tenant."""

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("length(id) > 0", name="ck_reservations_id"),
        CheckConstraint(
            "cpu >= 0 AND memory >= 0 AND gpu >= 0",
            name="ck_reservations_non_negative_resources",
        ),
        CheckConstraint(
            "(status = 'ACTIVE' AND released_at IS NULL) "
            "OR (status = 'RELEASED' AND released_at IS NOT NULL)",
            name="ck_reservations_release_state",
        ),
        Index("ix_reservations_tenant_created_at", "tenant_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("tenant_quotas.tenant_id", ondelete="RESTRICT"),
        nullable=False,
    )
    cpu: Mapped[int] = mapped_column(Integer)
    memory: Mapped[int] = mapped_column(Integer)
    gpu: Mapped[int] = mapped_column(Integer)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(
            ReservationStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
            create_constraint=True,
            name="reservation_status",
        ),
        default=ReservationStatus.ACTIVE,
        server_default=ReservationStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
