from app.exceptions import DuplicateShortCodeError
from app.models import ShortUrl

# IMPORTANT:
# models.py
# Defines what a ShortUrl is and what it can do to its own state.

# service.py
# Defines application use cases involving ShortUrl objects.

# repository.py
# Defines how ShortUrl objects are stored and retrieved.

# main.py / controller.py
# Accepts input and calls the service.

# Service check
# ↓
# Provides an early, friendly failure

# Repository/database constraint
#     ↓
# Provides the final correctness guarantee

# Important design boundary:
# def get(self, short_code: str) -> ShortUrl:
# short_url = self._urls.get(short_code)

# if short_url is None:
#     raise ShortCodeNotFoundError(short_code)

# if short_url.is_expired():
#     raise ShortUrlExpiredError(short_code)

# short_url.record_redirect()
# return short_url

# That mixes:
# Data access
# Expiration business rules
# Redirect behaviour
# Error decisions

# A cleaner split is:
# Repository:
#     Find and store objects

# Service:
#     Apply business rules and coordinate operations


class ShortUrlRepository:
    def __init__(self) -> None:
        # The key is the short code:
        # 'abc123'
        # The value is the complete domain object:
        # ShortUrl(
        #     short_code="abc123",
        #     destination_url="https://example.com",
        #     ...
        # )
        # So conceptually,
        # {
        #     "abc123": ShortUrl(...),
        #     "custom-name": ShortUrl(...),
        # }
        # The underscroe in '_urls' communicates:
        # This is internal repository state and should not normally be accessed directly from outside the class.
        self._urls: dict[str, ShortUrl] = {}

    def save(self, short_url: ShortUrl) -> ShortUrl:
        if short_url.short_code in self._urls:
            raise DuplicateShortCodeError(short_url.short_code)

        self._urls[short_url.short_code] = short_url
        return short_url

    def get(self, short_code: str) -> ShortUrl | None:
        return self._urls.get(short_code)

    def exists(self, short_code: str) -> bool:
        return short_code in self._urls

    def list_all(self) -> list[ShortUrl]:
        return list(self._urls.values())

    # PRODUCTION-GRADE CODE:
    # def delete(self, short_code: str) -> bool:
    #     if short_code not in self._urls:
    #         raise ShortCodeNotFoundError(short_code)
    #     # When failure is communicated through exceptions, returning True is unnecessary.
    #     # So need not to return True

    #     # Follow:
    #         # Do the operation.
    #         # Return nothing.
    #         # Raise if it cannot be completed.
    #     del self._urls[short_code]

    # Interview-optimised solution:
    # Why this version?
    # It exactly matches the requested contract.
    # It is concise.
    # It avoids repository-domain exception debates at this stage.
    # It supports a clean service layer.
    # It is easy to explain during code review.
    # It keeps “not found” as a normal repository result rather than an infrastructure failure.
    def delete(self, short_code: str) -> bool:
        deleted_url = self._urls.pop(short_code, None)
        return deleted_url is not None

    # The in-memory repository still uses domain-object mutation internally.
    def increment_redirect_count(
        self,
        short_code: str,
    ) -> ShortUrl | None:
        short_url = self.get(short_code)

        if short_url is None:
            return None

        short_url.record_redirect()

        return short_url
