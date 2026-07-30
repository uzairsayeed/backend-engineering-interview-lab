"""HTTP-level quota and reservation behavior tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.main import app


def configure_quota(
    client: TestClient,
    tenant_id: str,
    *,
    cpu: int = 4000,
    memory: int = 8192,
    gpu: int = 2,
):
    return client.put(
        f"/tenants/{tenant_id}/quota",
        json={"cpu": cpu, "memory": memory, "gpu": gpu},
    )


def create_reservation(
    client: TestClient,
    tenant_id: str,
    *,
    cpu: int,
    memory: int,
    gpu: int,
):
    return client.post(
        f"/tenants/{tenant_id}/reservations",
        json={"cpu": cpu, "memory": memory, "gpu": gpu},
    )


def test_configure_replace_and_retrieve_quota(client: TestClient) -> None:
    created = configure_quota(client, "tenant-a")
    assert created.status_code == 200
    assert created.json() == {
        "tenant_id": "tenant-a",
        "limit": {"cpu": 4000, "memory": 8192, "gpu": 2},
        "usage": {"cpu": 0, "memory": 0, "gpu": 0},
    }

    replaced = configure_quota(
        client,
        "tenant-a",
        cpu=8000,
        memory=16384,
        gpu=4,
    )
    assert replaced.status_code == 200
    assert replaced.json()["limit"] == {
        "cpu": 8000,
        "memory": 16384,
        "gpu": 4,
    }
    assert client.get("/tenants/tenant-a/quota").json() == replaced.json()


@pytest.mark.parametrize(
    "payload",
    [
        {"cpu": -1, "memory": 0, "gpu": 0},
        {"cpu": 0, "memory": -1, "gpu": 0},
        {"cpu": 0, "memory": 0, "gpu": -1},
        {"cpu": 1.5, "memory": 0, "gpu": 0},
        {"cpu": "1", "memory": 0, "gpu": 0},
    ],
)
def test_quantities_must_be_non_negative_integers(
    client: TestClient,
    payload: dict[str, object],
) -> None:
    response = client.put("/tenants/invalid/quota", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_missing_quota_returns_consistent_not_found(client: TestClient) -> None:
    response = client.get("/tenants/missing/quota")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "QUOTA_NOT_FOUND"


def test_quota_cannot_be_replaced_below_usage(client: TestClient) -> None:
    assert configure_quota(client, "tenant-a").status_code == 200
    assert create_reservation(
        client,
        "tenant-a",
        cpu=1000,
        memory=2048,
        gpu=1,
    ).status_code == 201

    response = configure_quota(
        client,
        "tenant-a",
        cpu=999,
        memory=1024,
        gpu=1,
    )
    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "QUOTA_BELOW_USAGE",
        "message": "Quota cannot be lower than current usage",
        "details": {"resources": ["cpu", "memory"]},
    }
    quota = client.get("/tenants/tenant-a/quota").json()
    assert quota["limit"] == {"cpu": 4000, "memory": 8192, "gpu": 2}
    assert quota["usage"] == {"cpu": 1000, "memory": 2048, "gpu": 1}


def test_reservation_lifecycle_and_idempotent_release(
    client: TestClient,
) -> None:
    assert configure_quota(client, "tenant-a").status_code == 200

    created = create_reservation(
        client,
        "tenant-a",
        cpu=1000,
        memory=2048,
        gpu=1,
    )
    assert created.status_code == 201
    reservation = created.json()
    reservation_id = reservation["id"]
    assert reservation["status"] == "ACTIVE"
    assert reservation["released_at"] is None

    retrieved = client.get(
        f"/tenants/tenant-a/reservations/{reservation_id}"
    )
    assert retrieved.status_code == 200
    assert retrieved.json() == reservation
    assert client.get("/tenants/tenant-a/reservations").json() == [reservation]
    assert client.get("/tenants/tenant-a/quota").json()["usage"] == {
        "cpu": 1000,
        "memory": 2048,
        "gpu": 1,
    }

    released = client.post(
        f"/tenants/tenant-a/reservations/{reservation_id}/release"
    )
    assert released.status_code == 200
    assert released.json()["status"] == "RELEASED"
    assert released.json()["released_at"] is not None

    released_again = client.post(
        f"/tenants/tenant-a/reservations/{reservation_id}/release"
    )
    assert released_again.status_code == 200
    assert released_again.json() == released.json()
    assert client.get("/tenants/tenant-a/quota").json()["usage"] == {
        "cpu": 0,
        "memory": 0,
        "gpu": 0,
    }


def test_reservation_is_all_or_nothing(client: TestClient) -> None:
    assert configure_quota(
        client,
        "tenant-a",
        cpu=1000,
        memory=1000,
        gpu=1,
    ).status_code == 200
    assert create_reservation(
        client,
        "tenant-a",
        cpu=800,
        memory=800,
        gpu=1,
    ).status_code == 201

    rejected = create_reservation(
        client,
        "tenant-a",
        cpu=201,
        memory=1,
        gpu=0,
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "QUOTA_EXCEEDED"
    assert len(client.get("/tenants/tenant-a/reservations").json()) == 1
    assert client.get("/tenants/tenant-a/quota").json()["usage"] == {
        "cpu": 800,
        "memory": 800,
        "gpu": 1,
    }


def test_tenants_are_isolated(client: TestClient) -> None:
    assert configure_quota(client, "tenant-a").status_code == 200
    assert configure_quota(client, "tenant-b").status_code == 200
    created = create_reservation(
        client,
        "tenant-a",
        cpu=1000,
        memory=1024,
        gpu=1,
    )
    reservation_id = created.json()["id"]

    assert client.get(
        f"/tenants/tenant-b/reservations/{reservation_id}"
    ).status_code == 404
    assert client.post(
        f"/tenants/tenant-b/reservations/{reservation_id}/release"
    ).status_code == 404
    assert client.get("/tenants/tenant-b/reservations").json() == []
    assert client.get("/tenants/tenant-b/quota").json()["usage"] == {
        "cpu": 0,
        "memory": 0,
        "gpu": 0,
    }
    assert client.get("/tenants/tenant-a/quota").json()["usage"] == {
        "cpu": 1000,
        "memory": 1024,
        "gpu": 1,
    }


def test_all_zero_reservation_is_allowed(client: TestClient) -> None:
    assert configure_quota(
        client,
        "tenant-a",
        cpu=0,
        memory=0,
        gpu=0,
    ).status_code == 200
    response = create_reservation(
        client,
        "tenant-a",
        cpu=0,
        memory=0,
        gpu=0,
    )
    assert response.status_code == 201


def test_database_error_is_hidden(client: TestClient) -> None:
    def failing_session():
        raise SQLAlchemyError("sensitive database details")

    app.dependency_overrides[get_db] = failing_session
    response = client.get("/tenants/tenant-a/quota")
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "DATABASE_ERROR",
            "message": "A database operation failed",
            "details": None,
        }
    }
    assert "sensitive" not in response.text
