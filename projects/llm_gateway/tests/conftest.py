"""Shared deterministic fixtures for provider and API tests."""

from collections.abc import AsyncIterator, Callable, Iterable

import httpx
import pytest

from app.config import ProviderSettings, Settings


class ChunkedAsyncStream(httpx.AsyncByteStream):
    """An in-memory stream that preserves configured byte boundaries."""

    def __init__(self, chunks: Iterable[bytes]) -> None:
        self._chunks = list(chunks)
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture
def settings() -> Settings:
    return Settings(
        provider_a=ProviderSettings(
            base_url="https://provider-a.test",
            api_key="provider-a-secret",
            model="provider-a-model",
        ),
        provider_b=ProviderSettings(
            base_url="https://provider-b.test",
            api_key="provider-b-secret",
            model="provider-b-model",
        ),
    )


@pytest.fixture
def client_factory() -> Callable[
    [httpx.MockTransport], httpx.AsyncClient
]:
    def create_client(transport: httpx.MockTransport) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport)

    return create_client


@pytest.fixture
def streaming_response() -> Callable[..., httpx.Response]:
    def create_response(
        *chunks: bytes, status_code: int = 200
    ) -> httpx.Response:
        return httpx.Response(
            status_code=status_code,
            headers={"Content-Type": "text/event-stream"},
            stream=ChunkedAsyncStream(chunks),
        )

    return create_response
