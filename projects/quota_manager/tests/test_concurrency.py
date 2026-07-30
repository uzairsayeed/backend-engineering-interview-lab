"""Concurrency tests using independent SQLAlchemy sessions."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain import QuotaExceededError, ReservationStatus
from app.models import Reservation, TenantQuota
from app.services import QuotaService, ReservationService


def test_concurrent_reservations_do_not_exceed_quota(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        QuotaService(session).replace_quota(
            "tenant-a",
            cpu_limit=4000,
            memory_limit=4000,
            gpu_limit=4,
        )

    barrier = Barrier(10)

    def reserve() -> str | None:
        with session_factory() as session:
            barrier.wait()
            try:
                reservation = ReservationService(session).create_reservation(
                    "tenant-a",
                    cpu=1000,
                    memory=1000,
                    gpu=1,
                )
                return reservation.id
            except QuotaExceededError:
                return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: reserve(), range(10)))

    successful_ids = [reservation_id for reservation_id in results if reservation_id]
    assert len(successful_ids) == 4
    assert len(set(successful_ids)) == 4

    with session_factory() as session:
        quota = session.get(TenantQuota, "tenant-a")
        assert quota is not None
        assert (quota.cpu_used, quota.memory_used, quota.gpu_used) == (
            4000,
            4000,
            4,
        )
        count = session.scalar(select(func.count()).select_from(Reservation))
        assert count == 4


def test_concurrent_release_decrements_usage_once(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        QuotaService(session).replace_quota(
            "tenant-a",
            cpu_limit=1000,
            memory_limit=1000,
            gpu_limit=1,
        )
    with session_factory() as session:
        reservation = ReservationService(session).create_reservation(
            "tenant-a",
            cpu=1000,
            memory=1000,
            gpu=1,
        )
        reservation_id = reservation.id

    barrier = Barrier(8)

    def release() -> ReservationStatus:
        with session_factory() as session:
            barrier.wait()
            return ReservationService(session).release_reservation(
                "tenant-a",
                reservation_id,
            ).status

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(lambda _: release(), range(8)))

    assert statuses == [ReservationStatus.RELEASED] * 8
    with session_factory() as session:
        quota = session.get(TenantQuota, "tenant-a")
        persisted = session.get(Reservation, reservation_id)
        assert quota is not None
        assert persisted is not None
        assert (quota.cpu_used, quota.memory_used, quota.gpu_used) == (0, 0, 0)
        assert persisted.status == ReservationStatus.RELEASED
        assert persisted.released_at is not None
