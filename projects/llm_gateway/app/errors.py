"""Sanitized gateway errors shared by service and HTTP layers."""


class GatewayError(Exception):
    """Base error safe to serialize in a public API response."""

    status_code: int = 500
    code: str = "internal_error"
    default_message: str = "An unexpected gateway error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class UpstreamError(GatewayError):
    """An upstream provider failed without an available fallback."""

    status_code = 502
    code = "upstream_error"
    default_message = "The upstream provider could not process the request."


class InvalidUpstreamResponseError(GatewayError):
    """An upstream provider returned malformed or unsupported data."""

    status_code = 502
    code = "invalid_upstream_response"
    default_message = "The upstream provider returned an invalid response."


class AllProvidersFailedError(GatewayError):
    """The primary triggered fallback and the backup also failed."""

    status_code = 503
    code = "all_providers_failed"
    default_message = "No provider is currently available."


class InternalGatewayError(GatewayError):
    """An unexpected internal failure occurred before streaming."""
