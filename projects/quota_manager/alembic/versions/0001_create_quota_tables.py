"""Create quota and reservation tables and seed tenants.

Revision ID: 0001
Revises:
Create Date: 2026-07-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial schema and deterministic development seed data."""

    op.create_table(
        "tenant_quotas",
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("cpu_limit", sa.Integer(), nullable=False),
        sa.Column("memory_limit", sa.Integer(), nullable=False),
        sa.Column("gpu_limit", sa.Integer(), nullable=False),
        sa.Column("cpu_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("memory_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gpu_used", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "length(tenant_id) > 0",
            name="ck_tenant_quotas_tenant_id",
        ),
        sa.CheckConstraint(
            "cpu_limit >= 0 AND memory_limit >= 0 AND gpu_limit >= 0",
            name="ck_tenant_quotas_non_negative_limits",
        ),
        sa.CheckConstraint(
            "cpu_used >= 0 AND memory_used >= 0 AND gpu_used >= 0",
            name="ck_tenant_quotas_non_negative_usage",
        ),
        sa.CheckConstraint(
            "cpu_used <= cpu_limit "
            "AND memory_used <= memory_limit "
            "AND gpu_used <= gpu_limit",
            name="ck_tenant_quotas_usage_within_limits",
        ),
        sa.PrimaryKeyConstraint("tenant_id"),
    )

    op.create_table(
        "reservations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("cpu", sa.Integer(), nullable=False),
        sa.Column("memory", sa.Integer(), nullable=False),
        sa.Column("gpu", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "RELEASED",
                name="reservation_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(id) > 0", name="ck_reservations_id"),
        sa.CheckConstraint(
            "cpu >= 0 AND memory >= 0 AND gpu >= 0",
            name="ck_reservations_non_negative_resources",
        ),
        sa.CheckConstraint(
            "(status = 'ACTIVE' AND released_at IS NULL) "
            "OR (status = 'RELEASED' AND released_at IS NOT NULL)",
            name="ck_reservations_release_state",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant_quotas.tenant_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reservations_tenant_created_at",
        "reservations",
        ["tenant_id", "created_at"],
    )

    quota_table = sa.table(
        "tenant_quotas",
        sa.column("tenant_id", sa.String),
        sa.column("cpu_limit", sa.Integer),
        sa.column("memory_limit", sa.Integer),
        sa.column("gpu_limit", sa.Integer),
        sa.column("cpu_used", sa.Integer),
        sa.column("memory_used", sa.Integer),
        sa.column("gpu_used", sa.Integer),
    )
    op.bulk_insert(
        quota_table,
        [
            {
                "tenant_id": f"tenant-{number}",
                "cpu_limit": 4000,
                "memory_limit": 8192,
                "gpu_limit": 2,
                "cpu_used": 0,
                "memory_used": 0,
                "gpu_used": 0,
            }
            for number in range(1, 6)
        ],
    )


def downgrade() -> None:
    """Remove the initial schema and its seed data."""

    op.drop_index(
        "ix_reservations_tenant_created_at",
        table_name="reservations",
    )
    op.drop_table("reservations")
    op.drop_table("tenant_quotas")
