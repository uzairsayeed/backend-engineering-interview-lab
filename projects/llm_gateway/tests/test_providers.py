"""Tests for provider request translation and SSE normalization."""

import json
from collections.abc import AsyncIterator, Callable

import httpx
import pytest

from app.config import Settings
from app.errors import InvalidUpstreamResponseError
from app.providers.base import (
    ContentEvent,
    DoneEvent,
    NormalizedEvent,
    ProviderStream,
)
from app.providers.provider_a import ProviderA
from app.providers.provider_b import ProviderB
from app.schemas import ChatCompletionRequest
from app.sse import SSEEvent, decode_sse


def chat_request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model="general-chat",
        messages=[
            {"role": "system", "content": "Follow instructions."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "How can I help?"},
        ],
        stream=True,
    )


async def collect_events(stream: ProviderStream) -> list[NormalizedEvent]:
    return [event async for event in stream.events]


@pytest.mark.asyncio
async def test_provider_a_translates_request_and_normalizes_stream(
    settings: Settings,
    client_factory: Callable[[httpx.MockTransport], httpx.AsyncClient],
    streaming_response: Callable[..., httpx.Response],
) -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return streaming_response(
            b'data: {"type":"content_',
            b'delta","text":"Hello"}\n\n',
            b'data: {"type":"content_delta","text":" from A"}\n\n',
            b'data: {"type":"done"}\n\n',
        )

    async with client_factory(httpx.MockTransport(handler)) as client:
        stream = await ProviderA(client, settings.provider_a).open_stream(
            chat_request()
        )
        events = await collect_events(stream)
        await stream.aclose()

    assert stream.status_code == 200
    assert stream.is_closed
    assert events == [
        ContentEvent(content="Hello"),
        ContentEvent(content=" from A"),
        DoneEvent(),
    ]

    upstream_request = captured_requests[0]
    assert upstream_request.method == "POST"
    assert str(upstream_request.url) == (
        "https://provider-a.test/v1/generate"
    )
    assert upstream_request.headers["Authorization"] == (
        "Bearer provider-a-secret"
    )
    assert upstream_request.headers["Content-Type"] == "application/json"
    assert json.loads(upstream_request.content) == {
        "model": "provider-a-model",
        "messages": [
            {"role": "system", "content": "Follow instructions."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "How can I help?"},
        ],
        "stream": True,
    }


@pytest.mark.asyncio
async def test_provider_b_translates_roles_and_normalizes_named_events(
    settings: Settings,
    client_factory: Callable[[httpx.MockTransport], httpx.AsyncClient],
    streaming_response: Callable[..., httpx.Response],
) -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return streaming_response(
            b"event: message\n",
            b'data: {"delta":{"content":"Hello"}}\n\n',
            b"event: message\n",
            b'data: {"delta":{"content":" from B"}}\n\n',
            b"event: done\n",
            b"data: {}\n\n",
        )

    async with client_factory(httpx.MockTransport(handler)) as client:
        stream = await ProviderB(client, settings.provider_b).open_stream(
            chat_request()
        )
        events = await collect_events(stream)
        await stream.aclose()

    assert stream.status_code == 200
    assert stream.is_closed
    assert events == [
        ContentEvent(content="Hello"),
        ContentEvent(content=" from B"),
        DoneEvent(),
    ]

    upstream_request = captured_requests[0]
    assert upstream_request.method == "POST"
    assert str(upstream_request.url) == (
        "https://provider-b.test/chat/stream"
    )
    assert upstream_request.headers["X-API-Key"] == "provider-b-secret"
    assert upstream_request.headers["Content-Type"] == "application/json"
    assert json.loads(upstream_request.content) == {
        "model": "provider-b-model",
        "conversation": [
            {"speaker": "system", "text": "Follow instructions."},
            {"speaker": "human", "text": "Hello"},
            {"speaker": "assistant", "text": "How can I help?"},
        ],
        "streaming": True,
    }


@pytest.mark.asyncio
async def test_sse_decoder_handles_comments_and_multiline_data() -> None:
    async def lines() -> AsyncIterator[str]:
        for line in (
            ": keep-alive",
            "event: message",
            'data: {"delta":',
            'data: {"content":"Hello"}}',
            "",
        ):
            yield line

    events = [event async for event in decode_sse(lines())]

    assert events == [
        SSEEvent(
            event="message",
            data='{"delta":\n{"content":"Hello"}}',
        )
    ]


@pytest.mark.asyncio
async def test_provider_a_rejects_malformed_json(
    settings: Settings,
    client_factory: Callable[[httpx.MockTransport], httpx.AsyncClient],
    streaming_response: Callable[..., httpx.Response],
) -> None:
    transport = httpx.MockTransport(
        lambda request: streaming_response(b"data: not-json\n\n")
    )

    async with client_factory(transport) as client:
        stream = await ProviderA(client, settings.provider_a).open_stream(
            chat_request()
        )
        with pytest.raises(InvalidUpstreamResponseError):
            await collect_events(stream)
        await stream.aclose()


@pytest.mark.asyncio
async def test_provider_b_rejects_message_without_content(
    settings: Settings,
    client_factory: Callable[[httpx.MockTransport], httpx.AsyncClient],
    streaming_response: Callable[..., httpx.Response],
) -> None:
    transport = httpx.MockTransport(
        lambda request: streaming_response(
            b"event: message\n",
            b'data: {"delta":{}}\n\n',
        )
    )

    async with client_factory(transport) as client:
        stream = await ProviderB(client, settings.provider_b).open_stream(
            chat_request()
        )
        with pytest.raises(InvalidUpstreamResponseError):
            await collect_events(stream)
        await stream.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["provider_a", "provider_b"])
async def test_provider_rejects_stream_without_done_event(
    provider_name: str,
    settings: Settings,
    client_factory: Callable[[httpx.MockTransport], httpx.AsyncClient],
    streaming_response: Callable[..., httpx.Response],
) -> None:
    if provider_name == "provider_a":
        chunks = (b'data: {"type":"content_delta","text":"partial"}\n\n',)
    else:
        chunks = (
            b"event: message\n",
            b'data: {"delta":{"content":"partial"}}\n\n',
        )

    transport = httpx.MockTransport(
        lambda request: streaming_response(*chunks)
    )
    async with client_factory(transport) as client:
        provider = (
            ProviderA(client, settings.provider_a)
            if provider_name == "provider_a"
            else ProviderB(client, settings.provider_b)
        )
        stream = await provider.open_stream(chat_request())
        with pytest.raises(InvalidUpstreamResponseError):
            await collect_events(stream)
        await stream.aclose()


@pytest.mark.asyncio
async def test_provider_stream_close_is_idempotent() -> None:
    close_count = 0

    async def events() -> AsyncIterator[NormalizedEvent]:
        if False:
            yield DoneEvent()

    async def close() -> None:
        nonlocal close_count
        close_count += 1

    stream = ProviderStream(
        status_code=200,
        events=events(),
        _close=close,
    )

    await stream.aclose()
    await stream.aclose()

    assert stream.is_closed
    assert close_count == 1
