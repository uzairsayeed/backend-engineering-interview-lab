from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_short_url_service
from app.main import app
from app.repository import ShortUrlRepository
from app.service import ShortUrlService

FIXED_TIME = datetime(
    2026,
    7,
    26,
    10,
    0,
    tzinfo=UTC,
)


@pytest.fixture
def fixed_time() -> datetime:
    """
    Provides a deterministic current time for API tests.

    Using a fixed clock prevents tests from depending on the
    actual time at which they are executed.
    """
    return FIXED_TIME


@pytest.fixture
def repository() -> ShortUrlRepository:
    """
    Creates a fresh in-memory repository for every test.

    This prevents data created by one test from leaking into
    another test.
    """
    return ShortUrlRepository()


@pytest.fixture
def test_service(
    repository: ShortUrlRepository,
    fixed_time: datetime,
) -> ShortUrlService:
    """
    Creates a service using the fresh test repository.

    The generated short code and current time are deterministic,
    making API responses predictable.
    """
    return ShortUrlService(
        repository=repository,
        code_generator=lambda: "abc123",
        clock=lambda: fixed_time,
    )


@pytest.fixture
def client(
    test_service: ShortUrlService,
) -> Iterator[TestClient]:
    """
    Creates a FastAPI TestClient and replaces the production
    ShortUrlService dependency with the isolated test service.

    All requests inside one test share the same repository.
    Separate tests receive separate repositories.
    """

    def override_short_url_service() -> ShortUrlService:
        return test_service

    app.dependency_overrides[get_short_url_service] = override_short_url_service

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
