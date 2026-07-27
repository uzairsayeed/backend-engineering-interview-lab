from app.dependencies import get_short_url_service
from app.service import ShortUrlService


def test_dependency_returns_short_url_service() -> None:
    service = get_short_url_service()

    assert isinstance(service, ShortUrlService)


def test_dependency_returns_same_service_instance() -> None:
    first_service = get_short_url_service()
    second_service = get_short_url_service()

    assert first_service is second_service
