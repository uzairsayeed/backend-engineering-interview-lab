from sqlalchemy import (
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database_models import ShortUrlRecord
from app.exceptions import DuplicateShortCodeError
from app.models import ShortUrl
from app.persistence_mappers import (
    to_short_url_domain,
    to_short_url_record,
)


SHORT_CODE_UNIQUE_CONSTRAINT = (
    "uq_short_urls_short_code"
)

# The SQL repository does not create its own session.
    # FastAPI dependency
    #     ↓ creates Session

    # SQLShortUrlRepository
    #     ↓ receives Session

    # ShortUrlService
    #     ↓ receives repository
class SQLShortUrlRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def save(
        self,
        short_url: ShortUrl,
    ) -> ShortUrl:
        record = to_short_url_record(
            short_url
        )

        try:
            with self._session.begin_nested():
                self._session.add(record)
                self._session.flush()
        except IntegrityError as error:
            if self._is_short_code_conflict(
                error
            ):
                raise DuplicateShortCodeError(
                    short_url.short_code
                ) from error

            raise

        return to_short_url_domain(record)

    def get(
        self,
        short_code: str,
    ) -> ShortUrl | None:
        record = self._get_record(short_code)

        if record is None:
            return None

        return to_short_url_domain(record)

    def exists(
        self,
        short_code: str,
    ) -> bool:
        statement = (
            select(ShortUrlRecord.id)
            .where(
                ShortUrlRecord.short_code
                == short_code
            )
            .limit(1)
        )

        record_id = self._session.scalar(
            statement
        )

        return record_id is not None

    def list_all(self) -> list[ShortUrl]:
        statement = (
            select(ShortUrlRecord)
            .order_by(ShortUrlRecord.id)
        )

        records = self._session.scalars(
            statement
        ).all()

        return [
            to_short_url_domain(record)
            for record in records
        ]

    def delete(
        self,
        short_code: str,
    ) -> bool:
        record = self._get_record(short_code)

        if record is None:
            return False

        self._session.delete(record)
        self._session.flush()

        return True

    def _get_record(
        self,
        short_code: str,
    ) -> ShortUrlRecord | None:
        statement = select(
            ShortUrlRecord
        ).where(
            ShortUrlRecord.short_code
            == short_code
        )

        result = self._session.execute(
            statement
        )

        return result.scalar_one_or_none()

    @staticmethod
    def _is_short_code_conflict(
        error: IntegrityError,
    ) -> bool:
        original_error = error.orig

        diagnostic = getattr(
            original_error,
            "diag",
            None,
        )

        constraint_name = getattr(
            diagnostic,
            "constraint_name",
            None,
        )

        if (
            constraint_name
            == SHORT_CODE_UNIQUE_CONSTRAINT
        ):
            return True

        error_message = str(
            original_error
        ).casefold()

        return (
            SHORT_CODE_UNIQUE_CONSTRAINT.casefold()
            in error_message
            or "short_urls.short_code"
            in error_message
        )

    def increment_redirect_count(
        self,
        short_code: str,
    ) -> ShortUrl | None:
        # Why not do this?
            # record.redirect_count += 1

            # That is a read-modify-write operation:
                # Read count = 10
                #     ↓
                # Python calculates 11
                #     ↓
                # Write count = 11
            # Two concurrent requests could both read 10 and both write 11.
            # The SQL expression:
                # Current database value
                #     ↓
                # Database adds 1
                #     ↓
                # Updated value
            # This is the important concurrency-safe part of the operation.
        statement = (
            update(ShortUrlRecord)
            .where(
                ShortUrlRecord.short_code
                == short_code
            )
            .values(
                redirect_count=(
                    ShortUrlRecord.redirect_count
                    + 1
                )
            )
        )

        result = self._session.execute(
            statement
        )

        if result.rowcount == 0:
            return None

        record = self._get_record(
            short_code
        )

        if record is None:
            return None

        return to_short_url_domain(record)