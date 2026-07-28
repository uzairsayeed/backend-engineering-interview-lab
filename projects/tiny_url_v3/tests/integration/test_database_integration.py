from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)

from app.database_models import Base
from app.dependencies import get_database_session
from app.main import app
from app.service import ShortUrlService
from app.sql_repository import SQLShortUrlRepository


FIXED_TIME = datetime(
    2026,
    7,
    27,
    10,
    0,
    tzinfo=UTC,
)


@pytest.fixture
def test_session_factory(
    tmp_path: Path,
) -> Iterator[sessionmaker[Session]]:
    database_path = (
        tmp_path / "tinyurl_integration.db"
    )

    test_engine = create_engine(
        f"sqlite:///{database_path}"
    )

    Base.metadata.create_all(
        bind=test_engine
    )

    session_factory = sessionmaker(
        bind=test_engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )

    try:
        yield session_factory
    finally:
        test_engine.dispose()

def test_url_and_redirect_count_persist_across_sessions(
    test_session_factory: sessionmaker[Session],
) -> None:
    # Session 1: create and commit the URL.
    with test_session_factory() as session:
        with session.begin():
            repository = SQLShortUrlRepository(
                session
            )

            service = ShortUrlService(
                repository=repository,
                clock=lambda: FIXED_TIME,
            )

            created = service.create_url(
                destination_url=(
                    "https://example.com/persisted"
                ),
                custom_code="persisted",
            )

            assert created.short_code == (
                "persisted"
            )
            assert created.redirect_count == 0

    # Session 2: resolve it and commit count = 1.
    with test_session_factory() as session:
        with session.begin():
            repository = SQLShortUrlRepository(
                session
            )

            service = ShortUrlService(
                repository=repository,
                clock=lambda: FIXED_TIME,
            )

            resolved = service.resolve_url(
                "persisted"
            )

            assert resolved.redirect_count == 1

    # Session 3: prove both values survived.
    with test_session_factory() as session:
        repository = SQLShortUrlRepository(
            session
        )

        service = ShortUrlService(
            repository=repository,
            clock=lambda: FIXED_TIME,
        )

        details = service.get_url_details(
            "persisted"
        )

        assert details.destination_url == (
            "https://example.com/persisted"
        )

        assert details.redirect_count == 1


def test_duplicate_database_alias_returns_409(
    test_session_factory: sessionmaker[Session],
) -> None:
    def override_database_session(
    ) -> Iterator[Session]:
        with test_session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides.clear()

    app.dependency_overrides[
        get_database_session
    ] = override_database_session

    client = TestClient(app)

    try:
        first_response = client.post(
            "/urls",
            json={
                "destination_url": (
                    "https://example.com/first"
                ),
                "custom_code": "duplicate",
            },
        )

        second_response = client.post(
            "/urls",
            json={
                "destination_url": (
                    "https://example.com/second"
                ),
                "custom_code": "duplicate",
            },
        )
    finally:
        client.close()
        app.dependency_overrides.clear()

    assert first_response.status_code == 201

    assert second_response.status_code == 409

    assert second_response.json()[
        "error"
    ]["code"] == "duplicate_short_code"