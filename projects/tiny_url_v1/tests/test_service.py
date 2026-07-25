from datetime import UTC, datetime, timedelta

import pytest

from app.exceptions import (
    DuplicateShortCodeError,
    InvalidExpirationError,
    ShortCodeGenerationError,
    ShortUrlExpiredError,
    ShortCodeNotFoundError
)
from app.models import ShortUrl
from app.repository import ShortUrlRepository
from app.service import ShortUrlService


FIXED_TIME = datetime(
    2026,
    7,
    25,
    10,
    0,
    tzinfo=UTC,
)


def fixed_clock() -> datetime:
    return FIXED_TIME


def test_create_url_with_custom_code() -> None:
    repository = ShortUrlRepository()

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    result = service.create_url(
        destination_url="https://example.com",
        custom_code="custom123",
    )

    assert result.short_code == "custom123"
    assert result.destination_url == "https://example.com"
    assert result.created_at == FIXED_TIME
    assert repository.get("custom123") == result


def test_create_url_with_generated_code() -> None:
    repository = ShortUrlRepository()

    service = ShortUrlService(
        repository=repository,
        code_generator=lambda: "abc123",
        clock=fixed_clock,
    )

    result = service.create_url(
        destination_url="https://example.com",
    )

    assert result.short_code == "abc123"
    assert repository.get("abc123") == result

def test_create_url_with_expiration() -> None:
    repository = ShortUrlRepository()

    service = ShortUrlService(
        repository=repository,
        code_generator=lambda: "abc123",
        clock=fixed_clock,
    )

    result = service.create_url(
        destination_url="https://example.com",
        expires_in_seconds=3600,
    )

    assert result.expires_at == (
        FIXED_TIME + timedelta(hours=1)
    )

def test_create_url_rejects_non_positive_expiration() -> None:
    repository = ShortUrlRepository()

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    with pytest.raises(InvalidExpirationError):
        service.create_url(
            destination_url="https://example.com",
            expires_in_seconds=0,
        )


def test_duplicate_custom_code_is_rejected() -> None:
    repository = ShortUrlRepository()

    repository.save(
        ShortUrl(
            short_code="custom123",
            destination_url="https://first.com",
            created_at=FIXED_TIME,
        )
    )

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    with pytest.raises(DuplicateShortCodeError):
        service.create_url(
            destination_url="https://second.com",
            custom_code="custom123",
        )

def test_generated_code_retries_after_collision() -> None:
    repository = ShortUrlRepository()

    repository.save(
        ShortUrl(
            short_code="taken",
            destination_url="https://existing.com",
            created_at=FIXED_TIME,
        )
    )

    generated_codes = iter(
        ["taken", "available"]
    )

    service = ShortUrlService(
        repository=repository,
        code_generator=lambda: next(generated_codes),
        clock=fixed_clock,
    )

    result = service.create_url(
        destination_url="https://example.com",
    )

    assert result.short_code == "available"

def test_generation_fails_after_maximum_attempts() -> None:
    repository = ShortUrlRepository()

    repository.save(
        ShortUrl(
            short_code="taken",
            destination_url="https://existing.com",
            created_at=FIXED_TIME,
        )
    )

    service = ShortUrlService(
        repository=repository,
        code_generator=lambda: "taken",
        clock=fixed_clock,
        max_generation_attempts=3,
    )

    with pytest.raises(ShortCodeGenerationError) as error:
        service.create_url(
            destination_url="https://example.com",
        )

    assert error.value.attempts == 3



def test_resolve_url_returns_saved_url() -> None:
    repository = ShortUrlRepository()

    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=FIXED_TIME,
    )

    repository.save(short_url)

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    result = service.resolve_url("abc123")

    assert result == short_url
    assert result.destination_url == "https://example.com"


def test_resolve_url_increments_redirect_count() -> None:
    repository = ShortUrlRepository()

    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=FIXED_TIME,
    )

    repository.save(short_url)

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    service.resolve_url("abc123")
    service.resolve_url("abc123")

    assert short_url.redirect_count == 2

def test_resolve_unknown_url_raises_not_found_error() -> None:
    repository = ShortUrlRepository()

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    with pytest.raises(ShortCodeNotFoundError) as error:
        service.resolve_url("missing")

    assert error.value.short_code == "missing"

def test_resolve_expired_url_raises_expired_error() -> None:
    repository = ShortUrlRepository()

    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=FIXED_TIME - timedelta(hours=2),
        expires_at=FIXED_TIME - timedelta(hours=1),
    )

    repository.save(short_url)

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    with pytest.raises(ShortUrlExpiredError):
        service.resolve_url("abc123")

    assert short_url.redirect_count == 0

def test_delete_url_removes_existing_url() -> None:
    repository = ShortUrlRepository()

    repository.save(
        ShortUrl(
            short_code="abc123",
            destination_url="https://example.com",
            created_at=FIXED_TIME,
        )
    )

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    result = service.delete_url("abc123")

    assert result is None
    assert repository.get("abc123") is None

def test_delete_unknown_url_raises_not_found_error() -> None:
    repository = ShortUrlRepository()

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    with pytest.raises(ShortCodeNotFoundError) as error:
        service.delete_url("missing")

    assert error.value.short_code == "missing"


def test_get_url_details_returns_saved_url() -> None:
    repository = ShortUrlRepository()
    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=FIXED_TIME,
    )
    repository.save(short_url)

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    result = service.get_url_details("abc123")

    assert result == short_url
    assert result.redirect_count == 0


def test_get_url_details_allows_expired_url() -> None:
    repository = ShortUrlRepository()
    short_url = ShortUrl(
        short_code="abc123",
        destination_url="https://example.com",
        created_at=FIXED_TIME - timedelta(hours=2),
        expires_at=FIXED_TIME - timedelta(hours=1),
    )
    repository.save(short_url)

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    result = service.get_url_details("abc123")

    assert result == short_url
    assert result.is_expired(FIXED_TIME) is True
    assert result.redirect_count == 0

def test_get_unknown_url_details_raises_not_found_error() -> None:
    repository = ShortUrlRepository()
    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    with pytest.raises(ShortCodeNotFoundError):
        service.get_url_details("missing")


def test_list_urls_returns_all_saved_urls() -> None:
    repository = ShortUrlRepository()
    first = ShortUrl(
        short_code="first",
        destination_url="https://first.com",
        created_at=FIXED_TIME,
    )
    second = ShortUrl(
        short_code="second",
        destination_url="https://second.com",
        created_at=FIXED_TIME,
    )

    repository.save(first)
    repository.save(second)

    service = ShortUrlService(
        repository=repository,
        clock=fixed_clock,
    )

    assert service.list_urls() == [first, second]