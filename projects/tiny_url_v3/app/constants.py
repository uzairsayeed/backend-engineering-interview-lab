SHORT_CODE_MIN_LENGTH = 3
SHORT_CODE_MAX_LENGTH = 32
SHORT_CODE_PATTERN = r"^[A-Za-z0-9_-]+$"


RESERVED_SHORT_CODES: frozenset[str] = frozenset(
    {
        "health",
        "urls",
        "docs",
        "redoc",
        "openapi.json",
    }
)