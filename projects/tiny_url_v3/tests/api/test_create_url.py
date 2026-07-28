from fastapi.testclient import TestClient


def test_create_url_with_custom_code(
    client: TestClient,
) -> None:
    response = client.post(
        "/urls",
        json={
            "destination_url": ("https://example.com/articles/python"),
            "custom_code": "python",
            "expires_in_seconds": 3600,
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["short_code"] == "python"
    assert body["destination_url"] == ("https://example.com/articles/python")
    assert body["short_url"] == ("http://127.0.0.1:8000/python")
    assert body["created_at"] == ("2026-07-26T10:00:00Z")
    assert body["expires_at"] == ("2026-07-26T11:00:00Z")
    assert body["redirect_count"] == 0

    assert response.headers["location"] == ("/urls/python")


def test_create_url_rejects_reserved_code(
    client: TestClient,
) -> None:
    response = client.post(
        "/urls",
        json={
            "destination_url": "https://example.com",
            "custom_code": "health",
        },
    )

    assert response.status_code == 409

    assert response.json() == {
        "error": {
            "code": "reserved_short_code",
            "message": ("Short code 'health' is reserved"),
        }
    }
