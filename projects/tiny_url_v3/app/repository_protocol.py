from typing import Protocol

from app.models import ShortUrl

# This is the storage contract required by the service.
    # ShortUrlService
    #         ↓ depends on
    # ShortUrlRepositoryProtocol
    #         ↑ implemented by
    #         ├── ShortUrlRepository
    #         └── SQLShortUrlRepository

# Why use Protocol?
    # A protocol uses structural typing.
    # The class does not need to explicitly inherit from the protocol:
        # It only needs to implement the required methods with compatible signatures.
from typing import Protocol

from app.models import ShortUrl


class ShortUrlRepositoryProtocol(
    Protocol
):
    def save(
        self,
        short_url: ShortUrl,
    ) -> ShortUrl:
        ...

    def get(
        self,
        short_code: str,
    ) -> ShortUrl | None:
        ...

    def exists(
        self,
        short_code: str,
    ) -> bool:
        ...

    def list_all(
        self,
    ) -> list[ShortUrl]:
        ...

    def delete(
        self,
        short_code: str,
    ) -> bool:
        ...

    def increment_redirect_count(
        self,
        short_code: str,
    ) -> ShortUrl | None:
        ...