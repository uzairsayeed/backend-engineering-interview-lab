from fastapi import (
    APIRouter,
    status,
)
from fastapi.responses import RedirectResponse

from app.api_types import ShortCodePath
from app.dependencies import ShortUrlServiceDependency
from app.schemas import ErrorResponse

router = APIRouter(
    tags=["Redirects"],
)


@router.get(
    "/{short_code}",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Redirect a short URL",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": ("No short URL exists for the supplied code."),
        },
        status.HTTP_410_GONE: {
            "model": ErrorResponse,
            "description": ("The short URL has expired."),
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": ("The short code does not satisfy the required format."),
        },
    },
)
def redirect_short_url(
    short_code: ShortCodePath,
    service: ShortUrlServiceDependency,
) -> RedirectResponse:
    short_url = service.resolve_url(short_code)

    return RedirectResponse(
        url=short_url.destination_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={
            "Cache-Control": "no-store",
        },
    )
