from datetime import UTC, datetime, timedelta
from app.models import ShortUrl


def test_url_without_expiration_never_expires() -> None:
    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=datetime.now(UTC),
    )

    assert short_url.is_expired() is False


def test_url_expires_after_expiration_time() -> None:
    current_time = datetime(2026, 7, 25, 10, 0, tzinfo=UTC)

    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=current_time - timedelta(days=2),
        expires_at=current_time - timedelta(seconds=1),
    )

    assert short_url.is_expired(current_time) is True


def test_url_is_active_before_expiration_time() -> None:
    current_time = datetime(2026, 7, 25, 10, 0, tzinfo=UTC)

    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=current_time,
        expires_at=current_time + timedelta(hours=1),
    )

    assert short_url.is_expired(current_time) is False


def test_record_redirect_increments_count() -> None:
    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=datetime.now(UTC),
    )

    short_url.record_redirect()
    short_url.record_redirect()

    assert short_url.redirect_count == 2    


def test_remaining_seconds_returns_none_without_expiration() -> None:
    current_time = datetime(2026, 7, 25, 10, 0, tzinfo=UTC)

    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=current_time,
    )

    assert short_url.remaining_seconds(current_time) is None


def test_remaining_seconds_returns_zero_when_expired() -> None:
    current_time = datetime(2026, 7, 25, 10, 0, tzinfo=UTC)

    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=current_time - timedelta(hours=1),
        expires_at=current_time - timedelta(seconds=10),
    )

    assert short_url.remaining_seconds(current_time) == 0


def test_remaining_seconds_returns_positive_seconds() -> None:
    current_time = datetime(2026, 7, 25, 10, 0, tzinfo=UTC)

    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=current_time,
        expires_at=current_time + timedelta(seconds=60),
    )

    assert short_url.remaining_seconds(current_time) == 60
