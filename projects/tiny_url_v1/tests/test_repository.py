from datetime import UTC, datetime

import pytest

from app.exceptions import DuplicateShortCodeError
from app.models import ShortUrl
from app.repository import ShortUrlRepository


def create_short_url(
    short_code: str = "abc123",
) -> ShortUrl:
    return ShortUrl(
        short_code=short_code,
        destination_url="https://example.com",
        created_at=datetime.now(UTC),
    )


def test_save_and_get_url() -> None:
    # This is also an example of 'Dependency Injection'
    # Each test creates its own fresh ShortUrlRepository() and passes it around. 
    # That's the spirit of DI — the test controls and owns the dependency, not the class under test.
    # DI = "don't build your tools yourself, receive them from whoever calls you."

    repository = ShortUrlRepository()
    short_url = create_short_url()

    repository.save(short_url)

    result = repository.get("abc123")

    assert result == short_url


def test_get_unknown_url_returns_none() -> None:
    repository = ShortUrlRepository()

    result = repository.get("missing")

    assert result is None


def test_exists_returns_true_for_saved_url() -> None:
    repository = ShortUrlRepository()
    repository.save(create_short_url())

    assert repository.exists("abc123") is True


def test_exists_returns_false_for_unknown_url() -> None:
    repository = ShortUrlRepository()

    assert repository.exists("missing") is False


def test_duplicate_short_code_is_rejected() -> None:
    repository = ShortUrlRepository()

    repository.save(create_short_url("abc123"))

    with pytest.raises(DuplicateShortCodeError):
        repository.save(create_short_url("abc123"))


def test_list_all_returns_saved_urls() -> None:
    repository = ShortUrlRepository()
    first = create_short_url("first")
    second = create_short_url("second")

    repository.save(first)
    repository.save(second)

    result = repository.list_all()

    assert result == [first, second]

def test_delete_existing_url_returns_true() -> None:
    repository = ShortUrlRepository()
    repository.save(create_short_url("abc123"))

    result = repository.delete("abc123")

    assert result is True
    assert repository.get("abc123") is None


def test_delete_unknown_url_returns_false() -> None:
    repository = ShortUrlRepository()

    result = repository.delete("missing_url")

    assert result is False