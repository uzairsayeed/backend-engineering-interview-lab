from fastapi.testclient import TestClient


def test_redirect_returns_temporary_redirect(
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

    response = client.get(
        "/python",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == ("https://example.com/articles/python")
    assert response.headers["cache-control"] == ("no-store")


def test_redirect_increments_redirect_count(
    client: TestClient,
) -> None:
    client.post(
        "/urls",
        json={
            "destination_url": ("https://example.com/articles/python"),
            "custom_code": "python",
        },
    )

    first_redirect = client.get(
        "/python",
        follow_redirects=False,
    )

    second_redirect = client.get(
        "/python",
        follow_redirects=False,
    )

    assert first_redirect.status_code == 307
    assert second_redirect.status_code == 307

    details_response = client.get("/urls/python")

    assert details_response.status_code == 200
    assert details_response.json()["redirect_count"] == 2


def test_redirect_unknown_url_returns_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        "/missing",
        follow_redirects=False,
    )

    assert response.status_code == 404

    assert response.json() == {
        "error": {
            "code": "short_code_not_found",
            "message": ("Short code 'missing' was not found"),
        }
    }


from datetime import timedelta

from app.models import ShortUrl
from app.repository import ShortUrlRepository
from tests.api.constants import FIXED_TIME


def test_redirect_expired_url_returns_gone(
    client: TestClient,
    repository: ShortUrlRepository,
) -> None:
    expired_url = ShortUrl(
        short_code="expired",
        destination_url="https://example.com/old",
        created_at=FIXED_TIME - timedelta(hours=2),
        expires_at=FIXED_TIME - timedelta(hours=1),
    )

    repository.save(expired_url)

    response = client.get(
        "/expired",
        follow_redirects=False,
    )

    assert response.status_code == 410

    assert response.json() == {
        "error": {
            "code": "short_url_expired",
            "message": ("Short URL 'expired' has expired"),
        }
    }

    assert expired_url.redirect_count == 0


def test_health_route_is_not_treated_as_short_code(
    client: TestClient,
) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
