class ShortUrlError(Exception):
    """Base exception for short URL domain errors."""


class ShortCodeNotFoundError(ShortUrlError):
    def __init__(self, short_code: str) -> None:
        super().__init__(f"Short code '{short_code}' was not found")
        self.short_code = short_code

class DuplicateShortCodeError(ShortUrlError):
    def __init__(self, short_code: str) -> None:
        super().__init__(f"Short code '{short_code}' already exists")
        self.short_code = short_code

class ShortUrlExpiredError(ShortUrlError):
    def __init__(self, short_code: str) -> None:
        super().__init__(f"Short code '{short_code}' has expired")
        self.short_code = short_code

class InvalidExpirationError(ShortUrlError):
    def __init__(self, expires_in_seconds: int) -> None:
        self.expires_in_seconds = expires_in_seconds
        super().__init__(
            "Expiration must be greater than zero seconds"
        )

class ShortCodeGenerationError(ShortUrlError):
    def __init__(self, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(
            f"Unable to generate a unique short code "
            f"after {attempts} attempts"
        )