import logging

APPLICATION_LOGGER_NAME = "tinyurl"

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(
    log_level: str,
) -> None:
    numeric_level = getattr(
        logging,
        log_level.upper(),
        None,
    )

    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    application_logger = logging.getLogger(APPLICATION_LOGGER_NAME)

    application_logger.setLevel(numeric_level)
    application_logger.propagate = False

    if not application_logger.handlers:
        handler = logging.StreamHandler()

        handler.setFormatter(logging.Formatter(LOG_FORMAT))

        application_logger.addHandler(handler)

    for handler in application_logger.handlers:
        handler.setLevel(numeric_level)
