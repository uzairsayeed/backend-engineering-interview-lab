"""Small provider contract shared by the routing service and adapters."""

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol

from app.schemas import ChatCompletionRequest


@dataclass(frozen=True, slots=True)
class ContentEvent:
    """One normalized client-visible text fragment."""

    content: str


@dataclass(frozen=True, slots=True)
class DoneEvent:
    """A normalized successful-completion marker."""


NormalizedEvent = ContentEvent | DoneEvent


@dataclass(slots=True)
class ProviderStream:
    """An opened provider response and its normalized event iterator."""

    status_code: int
    events: AsyncIterator[NormalizedEvent]
    _close: Callable[[], Awaitable[None]] = field(repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    @property
    def is_closed(self) -> bool:
        """Whether the upstream response has been closed."""

        return self._closed

    async def aclose(self) -> None:
        """Close the upstream response at most once."""

        if not self._closed:
            self._closed = True
            await self._close()


class Provider(Protocol):
    """Behavior required from each provider adapter."""

    async def open_stream(
        self, request: ChatCompletionRequest
    ) -> ProviderStream:
        """Open an upstream streaming response."""

        ...
