"""Domain vocabulary and business errors."""

from enum import StrEnum
from typing import Any


class ReservationStatus(StrEnum):
    """Possible reservation lifecycle states."""

    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class DomainError(Exception):
    """Base error raised when a business rule cannot be satisfied."""

    code = "DOMAIN_ERROR"
    message = "A domain rule was violated"

    def __init__(self, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(self.message)
        self.details = details


class QuotaNotFoundError(DomainError):
    code = "QUOTA_NOT_FOUND"
    message = "Quota is not configured for the tenant"


class QuotaBelowUsageError(DomainError):
    code = "QUOTA_BELOW_USAGE"
    message = "Quota cannot be lower than current usage"


class QuotaExceededError(DomainError):
    code = "QUOTA_EXCEEDED"
    message = "Insufficient quota for the requested resources"


class ReservationNotFoundError(DomainError):
    code = "RESERVATION_NOT_FOUND"
    message = "Reservation was not found for the tenant"
