# Why have a mapper?
# Our service returns:
# ShortUrl

# But the API promises:
# ShortUrlResponse

# The mapper converts between those representations:
# Domain model
#     ↓
# Mapping function
#     ↓
# HTTP response model

# It also creates the public short-link URL:
# http://127.0.0.1:8000/python
# That value does not belong in the core domain model because the hostname depends on the HTTP environment.

from app.models import ShortUrl
from app.schemas import ShortUrlResponse


def to_short_url_response(
    short_url: ShortUrl,
    public_base_url: str,
) -> ShortUrlResponse:
    normalised_base_url = public_base_url.rstrip("/")

    return ShortUrlResponse(
        short_code=short_url.short_code,
        destination_url=short_url.destination_url,
        short_url=(f"{normalised_base_url}/{short_url.short_code}"),
        created_at=short_url.created_at,
        expires_at=short_url.expires_at,
        redirect_count=short_url.redirect_count,
    )
