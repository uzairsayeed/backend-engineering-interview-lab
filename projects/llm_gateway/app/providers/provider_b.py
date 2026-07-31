"""Provider B request and streaming-response adapter."""

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
from app.schemas import ChatCompletionRequest, MessageRole
from app.sse import decode_sse

ROLE_TO_SPEAKER: dict[MessageRole, str] = {
    "system": "system",
    "user": "human",
    "assistant": "assistant",
}


class ProviderB:
    """Translate between the gateway contract and Provider B."""

    def __init__(
        self, client: httpx.AsyncClient, settings: ProviderSettings
    ) -> None:
        self._client = client
        self._settings = settings

    async def open_stream(
        self, request: ChatCompletionRequest
    ) -> ProviderStream:
        """Open Provider B's streaming endpoint."""

        upstream_request = self._client.build_request(
            "POST",
            f"{self._settings.base_url}/chat/stream",
            headers={
                "X-API-Key": self._settings.api_key,
                "Content-Type": "application/json",
            },
            json={
                "model": self._settings.model,
                "conversation": [
                    {
                        "speaker": ROLE_TO_SPEAKER[message.role],
                        "text": message.content,
                    }
                    for message in request.messages
                ],
                "streaming": True,
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

                if event.event == "message":
                    delta = payload.get("delta")
                    if not isinstance(delta, dict):
                        raise InvalidUpstreamResponseError()
                    content = delta.get("content")
                    if not isinstance(content, str):
                        raise InvalidUpstreamResponseError()
                    yield ContentEvent(content=content)
                    continue

                if event.event == "done":
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
