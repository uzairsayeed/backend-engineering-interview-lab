from functools import lru_cache
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
    app_version: str = "3.0.0"

    public_base_url: AnyHttpUrl = (
        "http://127.0.0.1:8000"
    )

    log_level: LogLevel = "INFO"

    database_url: str = (
        # sqlite:
        #     SQLAlchemy dialect

        # ///
        #     Relative file-based database

        # ./tinyurl.db
        #     File relative to the working directory
        "sqlite:///./tinyurl.db"
    )

    database_echo: bool = False

    model_config = SettingsConfigDict(
        env_prefix="TINYURL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()