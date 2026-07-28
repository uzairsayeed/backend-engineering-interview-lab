from dataclasses import dataclass
from datetime import UTC, datetime

# NOTES:
# When creating timestamps, use: datetime.now(UTC)
# IMPORTANT:
# models.py
# Defines what a ShortUrl is and what it can do to its own state.

# service.py
# Defines application use cases involving ShortUrl objects.

# repository.py
# Defines how ShortUrl objects are stored and retrieved.


# main.py / controller.py
# Accepts input and calls the service.
@dataclass
class ShortUrl:
    short_code: str
    destination_url: str
    created_at: datetime
    expires_at: datetime | None = (
        None  # The field may contain either: datetime or None. This is equivalent to Optional[datetime]
    )
    redirect_count: int = 0

    # Adding useful behaviour to the model
    # Why put these methods on the model?
    # These operations describe the state of a ShortUrl itself
    def is_expired(self, current_time: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False

        # Why accept current_time?
        # But time-dependent code becomes harder to test.
        now = current_time if current_time is not None else datetime.now(UTC)
        return self.expires_at <= now

    def record_redirect(self) -> None:
        self.redirect_count += 1

    def remaining_seconds(self, current_time: datetime | None = None) -> int | None:
        # A URL without expiration should return None, not 0.
        if self.expires_at is None:
            return None

        now = current_time if current_time is not None else datetime.now(UTC)
        seconds_remaining = int((self.expires_at - now).total_seconds())

        return max(0, seconds_remaining)
