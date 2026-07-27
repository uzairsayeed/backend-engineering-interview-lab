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

from functools import lru_cache
from typing import Annotated

# Depends is FastAPI's dependency injection mechanism.
# It tells FastAPI "before calling this route handler, run this function first and inject its return value."
from fastapi import Depends

from app.config import Settings
from app.repository import ShortUrlRepository
from app.service import ShortUrlService


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDependency = Annotated[
    Settings,
    Depends(get_settings),
]

# Creates one single instance of the repository (the _ prefix signals it's private/internal to this module).
_repository = ShortUrlRepository()

#  Creates one single instance of the service, injecting the repository into it.
# This is the Dependency Injection pattern — the service doesn't create its own repository, it receives one.
_service = ShortUrlService(
    repository=_repository,
)


def get_short_url_service() -> ShortUrlService:
    return _service


ShortUrlServiceDependency = Annotated[
    ShortUrlService,
    Depends(get_short_url_service),
]
