"""FastAPI application construction and shared-resource lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api import register_exception_handlers, router
from app.config import Settings
from app.providers.provider_a import ProviderA
from app.providers.provider_b import ProviderB
from app.service import ChatCompletionService

UPSTREAM_TIMEOUT = httpx.Timeout(
    connect=5.0,
    read=60.0,
    write=10.0,
    pool=5.0,
)


def create_app(
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Create the gateway application with injectable test dependencies."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        runtime_settings = settings or Settings.from_env()

        async with httpx.AsyncClient(
            transport=transport,
            timeout=UPSTREAM_TIMEOUT,
        ) as client:
            primary = ProviderA(client, runtime_settings.provider_a)
            backup = ProviderB(client, runtime_settings.provider_b)
            app.state.chat_completion_service = ChatCompletionService(
                primary=primary,
                backup=backup,
            )
            yield

    application = FastAPI(
        title="LLM Gateway",
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    application.include_router(router)
    return application


app = create_app()
