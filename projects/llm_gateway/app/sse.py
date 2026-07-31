"""Incremental Server-Sent Events decoding."""

from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SSEEvent:
    """One decoded SSE event."""

    event: str | None
    data: str


async def decode_sse(lines: AsyncIterable[str]) -> AsyncIterator[SSEEvent]:
    """Decode complete SSE events while retaining only the current event."""

    event_name: str | None = None
    data_lines: list[str] = []

    async for line in lines:
        if line == "":
            if event_name is not None or data_lines:
                yield SSEEvent(event=event_name, data="\n".join(data_lines))
            event_name = None
            data_lines = []
            continue

        if line.startswith(":"):
            continue

        field_name, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]

        if field_name == "event":
            event_name = value
        elif field_name == "data":
            data_lines.append(value)

    if event_name is not None or data_lines:
        yield SSEEvent(event=event_name, data="\n".join(data_lines))
