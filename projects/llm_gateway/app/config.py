"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlparse

PUBLIC_MODEL = "general-chat"


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is invalid."""


@dataclass(frozen=True, slots=True)
class ProviderSettings:
    """Connection settings for one upstream provider."""

    base_url: str
    api_key: str = field(repr=False)
    model: str

    def __post_init__(self) -> None:
        base_url = self.base_url.strip().rstrip("/")
        parsed_url = urlparse(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ConfigurationError(
                "Provider base URL must be an absolute HTTP or HTTPS URL."
            )
        if not self.api_key.strip():
            raise ConfigurationError("Provider API key must not be empty.")
        if not self.model.strip():
            raise ConfigurationError("Provider model must not be empty.")

        object.__setattr__(self, "base_url", base_url)
        object.__setattr__(self, "api_key", self.api_key.strip())
        object.__setattr__(self, "model", self.model.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime configuration for the gateway."""

    provider_a: ProviderSettings
    provider_b: ProviderSettings
    public_model: str = PUBLIC_MODEL

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Build settings from the process environment."""

        values = os.environ if environ is None else environ
        required_names = (
            "PROVIDER_A_BASE_URL",
            "PROVIDER_A_API_KEY",
            "PROVIDER_A_MODEL",
            "PROVIDER_B_BASE_URL",
            "PROVIDER_B_API_KEY",
            "PROVIDER_B_MODEL",
        )
        missing_names = [
            name for name in required_names if not values.get(name, "").strip()
        ]
        if missing_names:
            joined_names = ", ".join(missing_names)
            raise ConfigurationError(
                f"Missing required environment variables: {joined_names}"
            )

        return cls(
            provider_a=ProviderSettings(
                base_url=values["PROVIDER_A_BASE_URL"],
                api_key=values["PROVIDER_A_API_KEY"],
                model=values["PROVIDER_A_MODEL"],
            ),
            provider_b=ProviderSettings(
                base_url=values["PROVIDER_B_BASE_URL"],
                api_key=values["PROVIDER_B_API_KEY"],
                model=values["PROVIDER_B_MODEL"],
            ),
        )
