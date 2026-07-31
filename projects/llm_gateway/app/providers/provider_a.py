"""Provider A request and streaming-response adapter."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import ProviderSettings
from app.errors import InvalidUpstreamResponseError, UpstreamError
from app.providers.base import (
    ContentEvent,
    DoneEvent,
    NormalizedEvent,
    ProviderStream,
)
from app.schemas import ChatCompletionRequest
from app.sse import decode_sse


class ProviderA:
    """Translate between the gateway contract and Provider A."""

    def __init__(
        self, client: httpx.AsyncClient, settings: ProviderSettings
    ) -> None:
        self._client = client
        self._settings = settings

    async def open_stream(
        self, request: ChatCompletionRequest
    ) -> ProviderStream:
        """Open Provider A's streaming endpoint."""

        upstream_request = self._client.build_request(
            "POST",
            f"{self._settings.base_url}/v1/generate",
            headers={
                "Authorization": f"Bearer {self._settings.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._settings.model,
                "messages": [
                    message.model_dump() for message in request.messages
                ],
                "stream": True,
            },
        )
        try:
            response = await self._client.send(
                upstream_request, stream=True
            )
        except httpx.HTTPError as error:
            raise UpstreamError() from error

        return ProviderStream(
            status_code=response.status_code,
            events=self._normalized_events(response),
            _close=response.aclose,
        )

    async def _normalized_events(
        self, response: httpx.Response
    ) -> AsyncIterator[NormalizedEvent]:
        try:
            async for event in decode_sse(response.aiter_lines()):
                payload = self._parse_payload(event.data)
                event_type = payload.get("type")

                if event_type == "content_delta":
                    text = payload.get("text")
                    if not isinstance(text, str):
                        raise InvalidUpstreamResponseError()
                    yield ContentEvent(content=text)
                    continue

                if event_type == "done":
                    yield DoneEvent()
                    return

                raise InvalidUpstreamResponseError()

            raise InvalidUpstreamResponseError()
        except httpx.HTTPError as error:
            raise UpstreamError() from error

    @staticmethod
    def _parse_payload(data: str) -> dict[str, Any]:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError as error:
            raise InvalidUpstreamResponseError() from error

        if not isinstance(payload, dict):
            raise InvalidUpstreamResponseError()
        return payload
