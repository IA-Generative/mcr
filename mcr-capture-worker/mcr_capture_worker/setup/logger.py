import sys

from loguru import logger

from mcr_capture_worker.settings.settings import LoggingSettings

log_settings = LoggingSettings()


def setup_logging() -> None:
    logger.add(
        sys.stderr,
        format=get_log_format(),
        level=log_settings.LEVEL,
        colorize=log_settings.COLORIZE,
    )


def get_log_format() -> str:
    log_format = ""

    if log_settings.DISPLAY_TIMESTAMP:
        log_format += "<green>{time:HH:mm:ss.SSS}</green> | "
    log_format += "<level>{level: <8}</level> | "
    log_format += (
        "<cyan>{file.name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    )
    log_format += "<level>{message}</level>"

    return log_format
