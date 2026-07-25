# The service defines application use cases. 
# USECASE-1: For creation, it must:
    # Receive input
        # → choose or generate a short code
        # → calculate expiration
        # → create the model
        # → store it through the repository
        # → handle collisions
    
    # Decision 1: How should the service access the repository?
        # Production-grade version
            # Define an interface using Protocol.
        # Interview-optimised version
            # Inject the concrete repository

    # Decision 2: How should short codes be generated?
        # Naïve version
            # Generate directly inside create_url():
            # The problem is testing.
            # You cannot predict the generated code, making collision tests difficult.    
            # """
            #     def create_url(self, destination_url: str) -> ShortUrl:
            #         short_code = "".join(
            #             random.choices(string.ascii_letters + string.digits, k=6)
            #         )
            # """

        # Production-grade version
            # Create an explicit abstraction using Protocol

        # Interview-optimised version
            # Inject a callable

    # Decision 3: Should the service call exists() first?
        # A tempting implementation is:
            # """
            #     if self._repository.exists(generated_code):
            #         generate_another_code()

            #     return self._repository.save(short_url)
            # """
        # This is called a check-then-act pattern.

        # In a concurrent system:
            # Request A checks: code does not exist
            # Request B checks: code does not exist

            # Request A inserts code
            # Request B inserts the same code

        # The preliminary check cannot guarantee uniqueness.
        # The final guarantee must come from storage:
            # In-memory repository duplicate protection
            # or
            # Database UNIQUE constraint
        # Therefore, our service attempts to save directly.
        # This is safer and avoids an unnecessary lookup.

# USECASE-2: Resolve a short URL, the service must:
    # Receive short code
        # → find stored URL
        # → reject missing URL
        # → reject expired URL
        # → increment redirect count
        # → return destination URL

    # Decision 1: What should resolve_url() return?
        # Naïve version
            # """
                # def resolve_url(self, short_code: str) -> str | None:
                #     short_url = self._repository.get(short_code)

                #     if short_url is None:
                #         return None

                #     return short_url.destination_url
            # """
            # This works, but it loses useful information.
            # The caller cannot distinguish:
                # URL does not exist
                # URL exists but has expired
            # It also does not update the redirect count.

        # Production-grade version
            # A mature system might return a result object:
            # """
                # @dataclass(frozen=True)
                # class RedirectResult:
                #     destination_url: str
                #     short_code: str
                #     redirect_count: int
            # """

        
        # Interview-optimised version
            # Return the domain object:
            # """
                # def resolve_url(self, short_code: str) -> ShortUrl:
            # """
            # Why return the object instead of only the destination URL?
                # Because the API layer may need:
                    # destination_url
                    # short_code
                    # redirect_count
                    # expires_at
            # The service applies the business rules and returns the valid updated object.

# USECASE-3: Delete a short URL
    # Decision 1: Should delete be idempotent?
        # Naïve version:
            # """   
                # def delete_url(self, short_code: str) -> bool:
                #     return self._repository.delete(short_code)
            # """
        # The service adds no business meaning. The router must interpret the boolean.

        # Production-grade version:
            # A production service may define explicit semantics:
            # """
                # def delete_url(
                #     self,
                #     short_code: str,
                #     ignore_missing: bool = False,
                # ) -> None:
            # """

            # Or separate use cases:
            # """
                # delete_url()
                # delete_url_if_exists()
            # """

            # This prevents ambiguous behaviour.

        # Interview-optimised version
            # We will use strict deletion:
                # def delete_url(self, short_code: str) -> None:
            # If the repository returns False, raise ShortCodeNotFoundError.


from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import secrets
import string

from app.exceptions import (
    DuplicateShortCodeError,
    InvalidExpirationError,
    ShortCodeGenerationError,
    ShortCodeNotFoundError,
    ShortUrlExpiredError,
)
from app.models import ShortUrl
from app.repository import ShortUrlRepository

# Callable[[], str] → a function that takes no arguments and returns a string
CodeGenerator = Callable[[], str]
# Callable[[], datetime] → a function that takes no arguments and returns a datetime
Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )


class ShortUrlService:
    # The service has four dependencies or configuration values.
        # repository: Controls storage.
        # code_generator: Controls how generated aliases are created.
        # max_generation_attempts: Prevents an infinite loop if generated codes repeatedly collide.
    def __init__(
        self,
        repository: ShortUrlRepository,
        code_generator: CodeGenerator = generate_short_code,
        clock: Clock = utc_now,
        max_generation_attempts: int = 5,
    ) -> None:
        self._repository = repository
        self._code_generator = code_generator
        self._clock = clock
        self._max_generation_attempts = max_generation_attempts

    def create_url(
        self,
        destination_url: str,
        custom_code: str | None = None,
        expires_in_seconds: int | None = None,
    ) -> ShortUrl:
        created_at = self._clock()

        expires_at = self._calculate_expiration(
            created_at=created_at,
            expires_in_seconds=expires_in_seconds,
        )

        if custom_code is not None:
            short_url = ShortUrl(
                short_code=custom_code,
                destination_url=destination_url,
                created_at=created_at,
                expires_at=expires_at,
            )

            return self._repository.save(short_url)

        for _ in range(self._max_generation_attempts):
            generated_code = self._code_generator()

            short_url = ShortUrl(
                short_code=generated_code,
                destination_url=destination_url,
                created_at=created_at,
                expires_at=expires_at,
            )

            try:
                return self._repository.save(short_url)
            except DuplicateShortCodeError:
                continue

        raise ShortCodeGenerationError(
            self._max_generation_attempts
        )

    def resolve_url(self, short_code: str) -> ShortUrl:
        short_url = self._repository.get(short_code)

        if short_url is None:
            raise ShortCodeNotFoundError(short_code)

        current_time = self._clock()

        if short_url.is_expired(current_time):
            raise ShortUrlExpiredError(short_code)

        short_url.record_redirect()

        return short_url
    
    def delete_url(self, short_code: str) -> None:
        was_deleted = self.repository.delete(short_code)
        
        if not was_deleted:
            raise ShortCodeNotFoundError(short_code)

    def get_url_details(self, short_code: str) -> ShortUrl:
        short_url = self._repository.get(short_code)

        if short_url is None:
            raise ShortCodeNotFoundError(short_code)

        return short_url

    def list_urls(self) -> list[ShortUrl]:
        return self._repository.list_all()

    # staticmethod — doesn't need self, it's a pure utility function on the class. No access to instance state.
    @staticmethod
    def _calculate_expiration(
        created_at: datetime,
        expires_in_seconds: int | None,
    ) -> datetime | None:
        if expires_in_seconds is None:
            return None

        if expires_in_seconds <= 0:
            raise InvalidExpirationError(
                expires_in_seconds
            )

        return created_at + timedelta(
            seconds=expires_in_seconds
        )

    