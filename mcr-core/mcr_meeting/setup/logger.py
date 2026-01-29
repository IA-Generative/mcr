from __future__ import annotations

import logging
import re
import sys
from typing import Any

import loguru
from loguru import logger

from mcr_meeting.app.configs.base import LoggingSettings

log_setting = LoggingSettings()


def setup_logging() -> None:
    remove_all_default_handlers()
    create_loguru_handler()
    redirect_python_logging_to_loguru()


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore

        # Find caller to get correct stack depth
        frame, depth = logging.currentframe(), 2
        while frame.f_back and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def remove_all_default_handlers() -> None:
    # remove loguru default handler
    logger.remove()

    # remove python logging existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    loggers = (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "asyncio",
        "starlette",
    )

    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        # remove all handlers
        logging_logger.handlers = []
        # propagate to root logger so that it's handled by loguru
        logging_logger.propagate = True


def split_request_id_from_extra(record: loguru.Record) -> bool:
    extra = record["extra"]
    request_id = extra.pop("request_id", "------------------------------------")
    record["extra"] = {
        "extra_wo_request_id": str(extra) if extra else "",
        "request_id": request_id,
    }
    return True


ACCESS_LOG_UVICORN = re.compile(
    r'^\d{1,3}(?:\.\d{1,3}){3}:\d+ - "\w+ [^"]+ HTTP/[\d.]+" \d{3}$'
)


def loguru_filter(record: loguru.Record) -> bool:
    if record["name"] == "logging":
        msg = record["message"]
        if ACCESS_LOG_UVICORN.match(msg):
            return False
    return split_request_id_from_extra(record)


def create_loguru_handler() -> None:
    logger.add(
        sys.stderr,
        format=get_log_format(),
        level=log_setting.LEVEL,
        filter=loguru_filter,
        colorize=log_setting.COLORIZE,
    )


def redirect_python_logging_to_loguru() -> None:
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.DEBUG)


def get_log_format() -> str:
    log_format = ""

    if log_setting.DISPLAY_TIMESTAMP:
        log_format += "<green>{time:HH:mm:ss.SSS}</green> | "
    if log_setting.DISPLAY_REQUEST_ID:
        log_format += "<level>{extra[request_id]}</level> | "
    log_format += "<level>{level: <8}</level> | "
    log_format += (
        "<cyan>{file.name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    )
    log_format += "<level>{message}</level> <level>{extra[extra_wo_request_id]}</level>"

    return log_format


def log_ffmpeg_command(stream: Any) -> None:  # type: ignore[explicit-any]
    try:
        cmd = stream.compile()
        logger.debug("FFmpeg command: %s", " ".join(cmd))
    except Exception:
        logger.warning("Failed to compile FFmpeg command.")
        pass  # Don't fail if compile fails
