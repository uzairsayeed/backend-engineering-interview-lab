import pytest
from pydantic import ValidationError

from app.schemas import CreateShortUrlRequest


def test_create_request_accepts_valid_values() -> None:
    request = CreateShortUrlRequest(
        destination_url="https://example.com/page",
        custom_code="python-guide",
        expires_in_seconds=3600,
    )

    assert str(request.destination_url) == ("https://example.com/page")
    assert request.custom_code == "python-guide"
    assert request.expires_in_seconds == 3600


def test_optional_fields_default_to_none() -> None:
    request = CreateShortUrlRequest(
        destination_url="https://example.com",
    )

    assert request.custom_code is None
    assert request.expires_in_seconds is None


def test_invalid_destination_url_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CreateShortUrlRequest(
            destination_url="not-a-valid-url",
        )


def test_short_code_with_spaces_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CreateShortUrlRequest(
            destination_url="https://example.com",
            custom_code="python guide",
        )


def test_short_code_below_minimum_length_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CreateShortUrlRequest(
            destination_url="https://example.com",
            custom_code="ab",
        )


def test_non_positive_expiration_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CreateShortUrlRequest(
            destination_url="https://example.com",
            expires_in_seconds=0,
        )


def test_unexpected_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        CreateShortUrlRequest(
            destination_url="https://example.com",
            unknown_field="value",
        )
