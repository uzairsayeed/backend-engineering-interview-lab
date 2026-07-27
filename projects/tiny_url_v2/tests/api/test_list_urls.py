from fastapi.testclient import TestClient


def test_list_urls_returns_empty_list(
    client: TestClient,
) -> None:
    response = client.get("/urls")

    assert response.status_code == 200
    assert response.json() == []


def test_list_urls_returns_created_urls(
    client: TestClient,
) -> None:
    first_response = client.post(
        "/urls",
        json={
            "destination_url": "https://example.com/first",
            "custom_code": "first",
        },
    )

    second_response = client.post(
        "/urls",
        json={
            "destination_url": "https://example.com/second",
            "custom_code": "second",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = client.get("/urls")

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 2

    urls_by_code = {item["short_code"]: item for item in body}

    assert set(urls_by_code) == {
        "first",
        "second",
    }

    assert urls_by_code["first"]["destination_url"] == ("https://example.com/first")

    assert urls_by_code["second"]["destination_url"] == ("https://example.com/second")


def test_list_urls_does_not_increment_redirect_count(
    client: TestClient,
) -> None:
    client.post(
        "/urls",
        json={
            "destination_url": "https://example.com",
            "custom_code": "python",
        },
    )

    first_response = client.get("/urls")
    second_response = client.get("/urls")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert first_response.json()[0]["redirect_count"] == 0

    assert second_response.json()[0]["redirect_count"] == 0
