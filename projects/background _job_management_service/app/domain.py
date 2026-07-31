from enum import Enum


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobError(Exception):
    """Base class for expected job lifecycle errors."""


class JobNotFoundError(JobError):
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"Job {job_id} was not found")


class JobNotCancellableError(JobError):
    def __init__(self, job_id: str, status: JobStatus) -> None:
        self.job_id = job_id
        self.status = status
        super().__init__(
            f"Job {job_id} cannot be cancelled while in {status.value} state"
        )


class JobNotRetryableError(JobError):
    def __init__(self, job_id: str, status: JobStatus) -> None:
        self.job_id = job_id
        self.status = status
        super().__init__(f"Job {job_id} cannot be retried while in {status.value} state")


class RetryLimitExceededError(JobError):
    def __init__(self, job_id: str, retry_count: int) -> None:
        self.job_id = job_id
        self.retry_count = retry_count
        super().__init__(
            f"Job {job_id} has reached the retry limit of {retry_count}"
        )
