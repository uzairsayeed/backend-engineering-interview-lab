from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.models import ShortUrl
from app.repository import ShortUrlRepository


def test_get_url_details_returns_saved_url(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/urls",
        json={
            "destination_url": ("https://example.com/articles/python"),
            "custom_code": "python",
        },
    )

    assert create_response.status_code == 201

    response = client.get("/urls/python")

    assert response.status_code == 200

    assert response.json() == {
        "short_code": "python",
        "destination_url": ("https://example.com/articles/python"),
        "short_url": "http://127.0.0.1:8000/python",
        "created_at": "2026-07-26T10:00:00Z",
        "expires_at": None,
        "redirect_count": 0,
    }


def test_get_url_details_does_not_increment_redirect_count(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/urls",
        json={
            "destination_url": "https://example.com",
            "custom_code": "python",
        },
    )

    assert create_response.status_code == 201

    first_response = client.get("/urls/python")
    second_response = client.get("/urls/python")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert first_response.json()["redirect_count"] == 0
    assert second_response.json()["redirect_count"] == 0


def test_get_unknown_url_returns_not_found(
    client: TestClient,
) -> None:
    response = client.get("/urls/missing")

    assert response.status_code == 404

    assert response.json() == {
        "error": {
            "code": "short_code_not_found",
            "message": ("Short code 'missing' was not found"),
        }
    }


def test_get_url_details_allows_expired_url(
    client: TestClient,
    repository: ShortUrlRepository,
    fixed_time: datetime,
) -> None:
    expired_url = ShortUrl(
        short_code="expired",
        destination_url="https://example.com/old",
        created_at=fixed_time - timedelta(hours=2),
        expires_at=fixed_time - timedelta(hours=1),
    )

    repository.save(expired_url)

    response = client.get("/urls/expired")

    assert response.status_code == 200

    assert response.json() == {
        "short_code": "expired",
        "destination_url": "https://example.com/old",
        "short_url": "http://127.0.0.1:8000/expired",
        "created_at": "2026-07-26T08:00:00Z",
        "expires_at": "2026-07-26T09:00:00Z",
        "redirect_count": 0,
    }


def test_get_url_details_for_expired_url_does_not_increment_count(
    client: TestClient,
    repository: ShortUrlRepository,
    fixed_time: datetime,
) -> None:
    expired_url = ShortUrl(
        short_code="expired",
        destination_url="https://example.com/old",
        created_at=fixed_time - timedelta(hours=2),
        expires_at=fixed_time - timedelta(hours=1),
    )

    repository.save(expired_url)

    first_response = client.get("/urls/expired")
    second_response = client.get("/urls/expired")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert expired_url.redirect_count == 0
    assert second_response.json()["redirect_count"] == 0


def test_get_url_rejects_short_code_below_minimum_length(
    client: TestClient,
) -> None:
    response = client.get("/urls/ab")

    assert response.status_code == 422


def test_get_url_rejects_short_code_with_invalid_characters(
    client: TestClient,
) -> None:
    response = client.get("/urls/python!")

    assert response.status_code == 422
