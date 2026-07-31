from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain import JobStatus
from app.models import Job, utc_now


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, duration_seconds: int, should_fail: bool) -> Job:
        job = Job(
            duration_seconds=duration_seconds,
            should_fail=should_fail,
            status=JobStatus.PENDING,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: str) -> Job | None:
        statement = (
            select(Job)
            .where(Job.id == job_id)
            .execution_options(populate_existing=True)
        )
        return self.session.scalar(statement)

    def list_pending_ids(self) -> list[str]:
        statement = (
            select(Job.id)
            .where(Job.status == JobStatus.PENDING)
            .order_by(Job.created_at)
        )
        return list(self.session.scalars(statement))

    def claim(self, job_id: str) -> bool:
        now = utc_now()
        statement = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == JobStatus.PENDING,
            )
            .values(
                status=JobStatus.RUNNING,
                failure_reason=None,
                started_at=now,
                completed_at=None,
                updated_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )
        result = self.session.execute(statement)
        return result.rowcount == 1

    def cancel(self, job_id: str) -> bool:
        now = utc_now()
        statement = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == JobStatus.PENDING,
            )
            .values(
                status=JobStatus.CANCELLED,
                completed_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )
        result = self.session.execute(statement)
        return result.rowcount == 1

    def retry(self, job_id: str) -> bool:
        now = utc_now()
        statement = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == JobStatus.FAILED,
                Job.retry_count < 3,
            )
            .values(
                status=JobStatus.PENDING,
                retry_count=Job.retry_count + 1,
                failure_reason=None,
                started_at=None,
                completed_at=None,
                updated_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )
        result = self.session.execute(statement)
        return result.rowcount == 1

    def complete_successfully(self, job_id: str) -> bool:
        now = utc_now()
        statement = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == JobStatus.RUNNING,
            )
            .values(
                status=JobStatus.SUCCEEDED,
                failure_reason=None,
                completed_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )
        result = self.session.execute(statement)
        return result.rowcount == 1

    def complete_with_failure(self, job_id: str, reason: str) -> bool:
        now = utc_now()
        statement = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == JobStatus.RUNNING,
            )
            .values(
                status=JobStatus.FAILED,
                failure_reason=reason,
                completed_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )
        result = self.session.execute(statement)
        return result.rowcount == 1
