from typing import Literal

from pydantic import AnyHttpUrl
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

LogLevel = Literal[
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]


class Settings(BaseSettings):
    app_name: str = "TinyURL API"
    app_version: str = "2.0.0"

    public_base_url: AnyHttpUrl = "http://127.0.0.1:8000"

    log_level: LogLevel = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="TINYURL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
