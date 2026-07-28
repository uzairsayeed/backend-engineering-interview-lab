# The repository must convert between:
    # ShortUrl
    #     Domain object

    # ShortUrlRecord
    #     ORM persistence object

# Why mapping is necessary?
    # Domain to persistence
    # When saving:
        # ShortUrl
        #     ↓ to_short_url_record()
        # ShortUrlRecord
        #     ↓ session.add()
        # Database row

    # Persistence to domain
    # When reading:
        # Database row
        #     ↓ SQLAlchemy
        # ShortUrlRecord
        #     ↓ to_short_url_domain()
        # ShortUrl

    # The database-only id is deliberately omitted:
        # ShortUrlRecord:
        #     id
        #     short_code
        #     destination_url
        #     ...

        # ShortUrl:
        #     short_code
        #     destination_url
        #     ...

    # The domain does not care that the database assigned row ID 42.



from datetime import UTC, datetime

from app.database_models import ShortUrlRecord
from app.models import ShortUrl


def normalise_to_utc(
    value: datetime,
) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def to_short_url_record(
    short_url: ShortUrl,
) -> ShortUrlRecord:
    return ShortUrlRecord(
        short_code=short_url.short_code,
        destination_url=short_url.destination_url,
        created_at=normalise_to_utc(
            short_url.created_at
        ),
        expires_at=(
            normalise_to_utc(
                short_url.expires_at
            )
            if short_url.expires_at is not None
            else None
        ),
        redirect_count=short_url.redirect_count,
    )


def to_short_url_domain(
    record: ShortUrlRecord,
) -> ShortUrl:
    return ShortUrl(
        short_code=record.short_code,
        destination_url=record.destination_url,
        created_at=normalise_to_utc(
            record.created_at
        ),
        expires_at=(
            normalise_to_utc(
                record.expires_at
            )
            if record.expires_at is not None
            else None
        ),
        redirect_count=record.redirect_count,
    )