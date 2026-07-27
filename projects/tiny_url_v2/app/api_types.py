from typing import Annotated

from fastapi import Path

from app.schemas import (
    SHORT_CODE_MAX_LENGTH,
    SHORT_CODE_MIN_LENGTH,
    SHORT_CODE_PATTERN,
)

ShortCodePath = Annotated[
    str,
    Path(
        min_length=SHORT_CODE_MIN_LENGTH,
        max_length=SHORT_CODE_MAX_LENGTH,
        pattern=SHORT_CODE_PATTERN,
        description="The short code identifying the URL.",
        examples=["python-guide"],
    ),
]
