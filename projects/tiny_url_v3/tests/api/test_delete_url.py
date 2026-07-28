from fastapi.testclient import TestClient


def test_delete_existing_url_returns_no_content(
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

    delete_response = client.delete("/urls/python")

    assert delete_response.status_code == 204
    assert delete_response.content == b""


def test_deleted_url_can_no_longer_be_retrieved(
    client: TestClient,
) -> None:
    client.post(
        "/urls",
        json={
            "destination_url": "https://example.com",
            "custom_code": "python",
        },
    )

    delete_response = client.delete("/urls/python")

    details_response = client.get("/urls/python")

    redirect_response = client.get(
        "/python",
        follow_redirects=False,
    )

    assert delete_response.status_code == 204
    assert details_response.status_code == 404
    assert redirect_response.status_code == 404


def test_delete_unknown_url_returns_not_found(
    client: TestClient,
) -> None:
    response = client.delete("/urls/missing")

    assert response.status_code == 404

    assert response.json() == {
        "error": {
            "code": "short_code_not_found",
            "message": ("Short code 'missing' was not found"),
        }
    }


def test_delete_rejects_invalid_short_code(
    client: TestClient,
) -> None:
    response = client.delete("/urls/ab")

    assert response.status_code == 422


from datetime import timedelta

from app.models import ShortUrl
from app.repository import ShortUrlRepository
from tests.api.constants import FIXED_TIME


def test_delete_allows_expired_url(
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

    response = client.delete("/urls/expired")

    assert response.status_code == 204
    assert repository.get("expired") is None
