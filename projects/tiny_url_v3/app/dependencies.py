# IMPORTANT NOTES:
# The main requirement is:
# Every HTTP request must use the same in-memory repository while the server process is running.
# Otherwise, data created by one request will disappear before the next request.

# These objects [ _repository, _service ] are created at module import time:
# When Uvicorn imports the application: uvicorn app.main:app --reload
# Python imports app.dependencies when required.
# The repository and service are created once for that Python process:
# Application process starts
#         ↓
# Repository created once
#         ↓
# Service created once
#         ↓
# Request 1 uses service
# Request 2 uses same service
# Request 3 uses same service

# Why not inject the repository into the route?
# This would be possible:
# def create_url(
#     repository: ShortUrlRepositoryDependency,
# ):
# But routes should generally invoke application use cases through the service:
# Route
#     ↓
# Service
#     ↓
# Repository
# NOT:
# Route
# ↓
# Repository


from collections.abc import Iterator
from typing import Annotated

# Depends is FastAPI's dependency injection mechanism.
# It tells FastAPI "before calling this route handler, run this function first and inject its return value."
from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import (
    Settings,
    get_settings,
)
from app.database import SessionFactory
from app.service import ShortUrlService
from app.sql_repository import (
    SQLShortUrlRepository,
)


SettingsDependency = Annotated[
    Settings,
    Depends(get_settings),
]


# Understand the request transaction:
# Successful write request:
    # POST /urls
    #     ↓
    # get_database_session()
    #     ↓
    # Create Session
    #     ↓
    # Yield Session
    #     ↓
    # Create SQLShortUrlRepository
    #     ↓
    # Create ShortUrlService
    #     ↓
    # Route calls service.create_url()
    #     ↓
    # Repository INSERT + flush
    #     ↓
    # Route returns response model
    #     ↓
    # session.commit()
    #     ↓
    # Session context closes
    #     ↓
    # HTTP response sent
# Failed request:
    # POST /urls
    #     ↓
    # Repository/service raises
    #     ↓
    # Dependency catches Exception
    #     ↓
    # session.rollback()
    #     ↓
    # Exception re-raised
    #     ↓
    # Global exception handler
    #     ↓
    # 409 / 404 / 410 / 500
def get_database_session(
) -> Iterator[Session]:
    with SessionFactory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

# The scope="function" option is available in FastAPI 0.121 or later. 
# It ensures that dependency cleanup—where we commit or roll back—runs after the route handler finishes but before the response is sent.
DatabaseSessionDependency = Annotated[
    Session,
    Depends(
        get_database_session,
        scope="function",
    ),
]


def get_short_url_service(
    session: DatabaseSessionDependency,
) -> ShortUrlService:
    repository = SQLShortUrlRepository(
        session=session,
    )

    return ShortUrlService(
        repository=repository,
    )


ShortUrlServiceDependency = Annotated[
    ShortUrlService,
    Depends(get_short_url_service),
]