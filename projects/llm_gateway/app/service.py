"""Chat-completion stream orchestration."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.errors import (
    AllProvidersFailedError,
    GatewayError,
    InvalidUpstreamResponseError,
    UpstreamError,
)
from app.providers.base import (
    DoneEvent,
    NormalizedEvent,
    Provider,
    ProviderStream,
)
from app.schemas import ChatCompletionRequest

FALLBACK_STATUS_CODES = frozenset({429, 502, 503})


@dataclass(slots=True)
class PreparedStream:
    """A validated upstream stream ready for downstream iteration."""

    _upstream: ProviderStream = field(repr=False)
    _first_event: NormalizedEvent

    async def __aiter__(self) -> AsyncIterator[NormalizedEvent]:
        try:
            yield self._first_event
            if isinstance(self._first_event, DoneEvent):
                return

            try:
                async for event in self._upstream.events:
                    yield event
                    if isinstance(event, DoneEvent):
                        return
            except GatewayError:
                # Downstream headers may already have been sent. Ending without
                # DoneEvent distinguishes an interrupted stream from success.
                return
        finally:
            await self._upstream.aclose()


class ChatCompletionService:
    """Prepare a normalized stream using fixed primary/backup failover."""

    def __init__(self, primary: Provider, backup: Provider) -> None:
        self._primary = primary
        self._backup = backup

    async def prepare_stream(
        self, request: ChatCompletionRequest
    ) -> PreparedStream:
        """Select and validate a provider before downstream headers are sent."""

        upstream = await self._primary.open_stream(request)

        if upstream.status_code in FALLBACK_STATUS_CODES:
            await upstream.aclose()
            return await self._prepare_backup(request)

        if not 200 <= upstream.status_code < 300:
            await upstream.aclose()
            raise UpstreamError()

        return await self._prefetch(upstream)

    async def _prepare_backup(
        self, request: ChatCompletionRequest
    ) -> PreparedStream:
        try:
            upstream = await self._backup.open_stream(request)
        except GatewayError as error:
            raise AllProvidersFailedError() from error

        if not 200 <= upstream.status_code < 300:
            await upstream.aclose()
            raise AllProvidersFailedError()

        try:
            return await self._prefetch(upstream)
        except GatewayError as error:
            raise AllProvidersFailedError() from error

    @staticmethod
    async def _prefetch(upstream: ProviderStream) -> PreparedStream:
        try:
            first_event = await anext(upstream.events)
            return PreparedStream(
                _upstream=upstream,
                _first_event=first_event,
            )
        except StopAsyncIteration as error:
            await upstream.aclose()
            raise InvalidUpstreamResponseError() from error
        except BaseException:
            await upstream.aclose()
            raise
