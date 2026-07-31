"""End-to-end tests for streaming, fallback, and failure behavior."""

from collections.abc import AsyncIterator, Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.providers.base import ContentEvent, DoneEvent, ProviderStream
from app.providers.provider_a import ProviderA
from app.providers.provider_b import ProviderB
from app.schemas import ChatCompletionRequest
from app.service import ChatCompletionService


def valid_payload() -> dict[str, object]:
    return {
        "model": "general-chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    }


def create_test_client(
    settings: Settings,
    handler: Callable[[httpx.Request], httpx.Response],
) -> TestClient:
    app = create_app(
        settings=settings,
        transport=httpx.MockTransport(handler),
    )
    return TestClient(app, raise_server_exceptions=False)


def test_health_does_not_call_upstream_provider(settings: Settings) -> None:
    provider_called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal provider_called
        provider_called = True
        raise AssertionError("Health check must not call a provider")

    with create_test_client(settings, handler) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert provider_called is False


def test_primary_success_streams_normalized_sse(
    settings: Settings,
    streaming_response: Callable[..., httpx.Response],
) -> None:
    upstream_responses: list[httpx.Response] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = streaming_response(
            b'data: {"type":"content_delta","text":"Hello"}\n\n',
            b'data: {"type":"content_delta","text":" world"}\n\n',
            b'data: {"type":"done"}\n\n',
        )
        upstream_responses.append(response)
        return response

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=valid_payload())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert response.text == (
        'data: {"choices":[{"index":0,"delta":{"content":"Hello"}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"content":" world"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    assert upstream_responses[0].is_closed


def test_validation_error_is_normalized_without_calling_provider(
    settings: Settings,
) -> None:
    provider_called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal provider_called
        provider_called = True
        raise AssertionError("Provider must not be called")

    payload = valid_payload()
    payload["stream"] = False

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"] == "Request validation failed."
    assert response.json()["error"]["details"]
    assert provider_called is False


def test_invalid_first_event_returns_502_before_sse_starts(
    settings: Settings,
    streaming_response: Callable[..., httpx.Response],
) -> None:
    upstream_responses: list[httpx.Response] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = streaming_response(b"data: not-json\n\n")
        upstream_responses.append(response)
        return response

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=valid_payload())

    assert response.status_code == 502
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "error": {
            "code": "invalid_upstream_response",
            "message": "The upstream provider returned an invalid response.",
        }
    }
    assert upstream_responses[0].is_closed


def test_primary_failure_status_returns_sanitized_502(
    settings: Settings,
    streaming_response: Callable[..., httpx.Response],
) -> None:
    upstream_responses: list[httpx.Response] = []
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        response = streaming_response(
            b'{"provider_error":"do not expose"}',
            status_code=500,
        )
        upstream_responses.append(response)
        return response

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=valid_payload())

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "upstream_error",
            "message": "The upstream provider could not process the request.",
        }
    }
    assert "provider_error" not in response.text
    assert upstream_responses[0].is_closed
    assert requested_hosts == ["provider-a.test"]


def test_empty_primary_stream_returns_502_before_sse_starts(
    settings: Settings,
    streaming_response: Callable[..., httpx.Response],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return streaming_response()

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=valid_payload())

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_upstream_response"


@pytest.mark.parametrize("primary_status", [429, 502, 503])
def test_required_primary_status_silently_falls_back_to_provider_b(
    primary_status: int,
    settings: Settings,
    streaming_response: Callable[..., httpx.Response],
) -> None:
    requested_hosts: list[str] = []
    upstream_responses: list[httpx.Response] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)

        if request.url.host == "provider-a.test":
            response = streaming_response(
                b'{"private_provider_a_error":"hidden"}',
                status_code=primary_status,
            )
        else:
            assert upstream_responses[0].is_closed
            response = streaming_response(
                b"event: message\n",
                b'data: {"delta":{"content":"Backup answer"}}\n\n',
                b"event: done\n",
                b"data: {}\n\n",
            )

        upstream_responses.append(response)
        return response

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=valid_payload())

    assert response.status_code == 200
    assert response.text == (
        'data: {"choices":[{"index":0,"delta":'
        '{"content":"Backup answer"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    assert "private_provider_a_error" not in response.text
    assert requested_hosts == ["provider-a.test", "provider-b.test"]
    assert all(item.is_closed for item in upstream_responses)


def test_both_providers_failing_before_stream_returns_503(
    settings: Settings,
    streaming_response: Callable[..., httpx.Response],
) -> None:
    requested_hosts: list[str] = []
    upstream_responses: list[httpx.Response] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        status_code = 503 if request.url.host == "provider-a.test" else 500
        response = streaming_response(
            b'{"provider_error":"hidden"}',
            status_code=status_code,
        )
        upstream_responses.append(response)
        return response

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=valid_payload())

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "all_providers_failed",
            "message": "No provider is currently available.",
        }
    }
    assert "provider_error" not in response.text
    assert requested_hosts == ["provider-a.test", "provider-b.test"]
    assert all(item.is_closed for item in upstream_responses)


def test_invalid_backup_first_event_returns_503(
    settings: Settings,
    streaming_response: Callable[..., httpx.Response],
) -> None:
    upstream_responses: list[httpx.Response] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = (
            streaming_response(status_code=503)
            if request.url.host == "provider-a.test"
            else streaming_response(b"event: message\ndata: not-json\n\n")
        )
        upstream_responses.append(response)
        return response

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=valid_payload())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "all_providers_failed"
    assert all(item.is_closed for item in upstream_responses)


def test_malformed_event_after_partial_output_ends_without_done(
    settings: Settings,
    streaming_response: Callable[..., httpx.Response],
) -> None:
    upstream_responses: list[httpx.Response] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = streaming_response(
            b'data: {"type":"content_delta","text":"partial"}\n\n',
            b"data: not-json\n\n",
        )
        upstream_responses.append(response)
        return response

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=valid_payload())

    assert response.status_code == 200
    assert response.text == (
        'data: {"choices":[{"index":0,"delta":{"content":"partial"}}]}\n\n'
    )
    assert "[DONE]" not in response.text
    assert upstream_responses[0].is_closed


class DisconnectingStream(httpx.AsyncByteStream):
    """Yield one valid event, then simulate an upstream disconnection."""

    def __init__(self) -> None:
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b'data: {"type":"content_delta","text":"partial"}\n\n'
        raise httpx.ReadError("Provider disconnected")

    async def aclose(self) -> None:
        self.closed = True


def test_disconnect_after_partial_output_ends_without_done(
    settings: Settings,
) -> None:
    upstream_stream = DisconnectingStream()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, stream=upstream_stream)

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=valid_payload())

    assert response.status_code == 200
    assert response.text == (
        'data: {"choices":[{"index":0,"delta":{"content":"partial"}}]}\n\n'
    )
    assert "[DONE]" not in response.text
    assert upstream_stream.closed


def test_primary_connection_error_returns_502_without_fallback(
    settings: Settings,
) -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        raise httpx.ConnectError("Connection failed", request=request)

    with create_test_client(settings, handler) as client:
        response = client.post("/v1/chat/completions", json=valid_payload())

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_error"
    assert requested_hosts == ["provider-a.test"]


@pytest.mark.asyncio
async def test_stopping_downstream_iteration_closes_upstream(
    settings: Settings,
    streaming_response: Callable[..., httpx.Response],
) -> None:
    upstream_responses: list[httpx.Response] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = streaming_response(
            b'data: {"type":"content_delta","text":"first"}\n\n',
            b'data: {"type":"content_delta","text":"second"}\n\n',
            b'data: {"type":"done"}\n\n',
        )
        upstream_responses.append(response)
        return response

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        service = ChatCompletionService(
            primary=ProviderA(client, settings.provider_a),
            backup=ProviderB(client, settings.provider_b),
        )
        prepared = await service.prepare_stream(
            ChatCompletionRequest.model_validate(valid_payload())
        )
        iterator = aiter(prepared)

        await anext(iterator)
        await iterator.aclose()

    assert upstream_responses[0].is_closed


@pytest.mark.asyncio
async def test_prepared_stream_consumes_upstream_incrementally() -> None:
    produced_events = 0
    upstream_closed = False

    async def events() -> AsyncIterator[ContentEvent | DoneEvent]:
        nonlocal produced_events
        for content in ("first", "second", "third"):
            produced_events += 1
            yield ContentEvent(content=content)
        produced_events += 1
        yield DoneEvent()

    async def close() -> None:
        nonlocal upstream_closed
        upstream_closed = True

    class ControlledProvider:
        async def open_stream(
            self, request: ChatCompletionRequest
        ) -> ProviderStream:
            return ProviderStream(
                status_code=200,
                events=events(),
                _close=close,
            )

    provider = ControlledProvider()
    service = ChatCompletionService(primary=provider, backup=provider)

    prepared = await service.prepare_stream(
        ChatCompletionRequest.model_validate(valid_payload())
    )
    assert produced_events == 1

    downstream = aiter(prepared)
    first_event = await anext(downstream)
    assert first_event == ContentEvent(content="first")
    assert produced_events == 1

    second_event = await anext(downstream)
    assert second_event == ContentEvent(content="second")
    assert produced_events == 2

    await downstream.aclose()
    assert upstream_closed
