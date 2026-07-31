from sqlalchemy.orm import Session

from app.domain import (
    JobNotCancellableError,
    JobNotFoundError,
    JobNotRetryableError,
    JobStatus,
    RetryLimitExceededError,
)
from app.models import Job
from app.repository import JobRepository
from app.schemas import JobCreate


class JobService:
    def __init__(self, session: Session) -> None:
        self.repository = JobRepository(session)

    def create(self, data: JobCreate) -> Job:
        return self.repository.create(
            duration_seconds=data.duration_seconds,
            should_fail=data.should_fail,
        )

    def get(self, job_id: str) -> Job:
        job = self.repository.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job

    def list_pending_ids(self) -> list[str]:
        return self.repository.list_pending_ids()

    def cancel(self, job_id: str) -> Job:
        if self.repository.cancel(job_id):
            return self.get(job_id)

        job = self.get(job_id)
        raise JobNotCancellableError(job.id, job.status)

    def retry(self, job_id: str) -> Job:
        if self.repository.retry(job_id):
            return self.get(job_id)

        job = self.get(job_id)
        if job.status != JobStatus.FAILED:
            raise JobNotRetryableError(job.id, job.status)
        raise RetryLimitExceededError(job.id, job.retry_count)

    def claim(self, job_id: str) -> Job | None:
        if not self.repository.claim(job_id):
            return None
        return self.get(job_id)

    def complete_successfully(self, job_id: str) -> Job | None:
        if not self.repository.complete_successfully(job_id):
            return None
        return self.get(job_id)

    def complete_with_failure(self, job_id: str, reason: str) -> Job | None:
        if not self.repository.complete_with_failure(job_id, reason):
            return None
        return self.get(job_id)
