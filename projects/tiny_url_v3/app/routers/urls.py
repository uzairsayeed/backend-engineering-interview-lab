# No route-level try/except
# We do not need:
# try:
#     short_url = service.get_url_details(short_code)
# except ShortCodeNotFoundError as error:
#     ...

# Our global exception handler already translates:
# ShortCodeNotFoundError
#         ↓
# 404 Not Found

# The route stays focused on its successful use case:
# short_url = service.get_url_details(short_code)
# return to_short_url_response(...)

# Route:
#     Implements successful flow

# Domain handler:
#     Handles expected ShortUrlError

# Validation handler:
#     Handles malformed requests

# Unexpected handler:
#     Logs and returns safe 500


from fastapi import (
    APIRouter,
    Response,
    status,
)

from app.api_docs import VALIDATION_ERROR_RESPONSE
from app.api_types import ShortCodePath
from app.dependencies import (
    SettingsDependency,
    ShortUrlServiceDependency,
)
from app.mappers import to_short_url_response
from app.schemas import (
    CreateShortUrlRequest,
    ErrorResponse,
    ShortUrlResponse,
)

router = APIRouter(
    prefix="/urls",
    tags=["URLs"],
)


@router.post(
    "",
    response_model=ShortUrlResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a short URL",
    responses={
        **VALIDATION_ERROR_RESPONSE,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": ("The custom code already exists or is reserved."),
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": ("A unique generated code could not be created."),
        },
    },
)
def create_short_url(
    payload: CreateShortUrlRequest,
    response: Response,
    service: ShortUrlServiceDependency,
    settings: SettingsDependency,
) -> ShortUrlResponse:
    short_url = service.create_url(
        destination_url=str(payload.destination_url),
        custom_code=payload.custom_code,
        expires_in_seconds=payload.expires_in_seconds,
    )

    response.headers["Location"] = f"/urls/{short_url.short_code}"

    return to_short_url_response(
        short_url=short_url,
        public_base_url=str(settings.public_base_url),
    )


@router.get(
    "/{short_code}",
    response_model=ShortUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get short URL details",
    responses={
        **VALIDATION_ERROR_RESPONSE,
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": ("No short URL exists for the supplied code."),
        },
    },
)
def get_short_url_details(
    short_code: ShortCodePath,
    service: ShortUrlServiceDependency,
    settings: SettingsDependency,
) -> ShortUrlResponse:
    short_url = service.get_url_details(short_code)

    return to_short_url_response(
        short_url=short_url,
        public_base_url=str(settings.public_base_url),
    )


@router.get(
    "",
    response_model=list[ShortUrlResponse],
    status_code=status.HTTP_200_OK,
    summary="List short URLs",
)
def list_short_urls(
    service: ShortUrlServiceDependency,
    settings: SettingsDependency,
) -> list[ShortUrlResponse]:
    public_base_url = str(settings.public_base_url)

    return [
        to_short_url_response(
            short_url=short_url,
            public_base_url=public_base_url,
        )
        for short_url in service.list_urls()
    ]


@router.delete(
    "/{short_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a short URL",
    responses={
        **VALIDATION_ERROR_RESPONSE,
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": ("No short URL exists for the supplied code."),
        },
    },
)
def delete_short_url(
    short_code: ShortCodePath,
    service: ShortUrlServiceDependency,
) -> Response:
    service.delete_url(short_code)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
