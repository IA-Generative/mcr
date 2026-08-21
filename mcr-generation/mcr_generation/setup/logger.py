from __future__ import annotations

import json
import logging
import re
import sys
import traceback

import loguru
from loguru import logger

from mcr_generation.app.configs.settings import LoggingSettings

log_settings = LoggingSettings()

_SERVICE_NAME = "mcr-generation"


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
            level = record.levelno  # type: ignore[assignment]
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
        "asyncio",
        "starlette",
    )

    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        # remove all handlers
        logging_logger.handlers = []
        # propagate to root logger so that it's handled by loguru
        logging_logger.propagate = True


ACCESS_LOG_UVICORN = re.compile(
    r'^\d{1,3}(?:\.\d{1,3}){3}:\d+ - "\w+ [^"]+ HTTP/[\d.]+" \d{3}$'
)


def loguru_filter(record: loguru.Record) -> bool:
    if record["name"] == "logging":
        msg = record["message"]
        if ACCESS_LOG_UVICORN.match(msg):
            return False
    return True


def _serialize_record(
    record: loguru.Record, trace_id: str | None, span_id: str | None
) -> str:
    payload = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "service": _SERVICE_NAME,
        "logger": record["name"],
        "file": record["file"].name,
        "line": record["line"],
        "trace_id": trace_id,
        "span_id": span_id,
        "request_id": record["extra"].get("request_id"),
    }
    exception = record["exception"]
    if exception is not None:
        payload["exception"] = "".join(
            traceback.format_exception(
                exception.type, exception.value, exception.traceback
            )
        )
    user_extra = {k: v for k, v in record["extra"].items() if k != "request_id"}
    if user_extra:
        payload["extra"] = user_extra
    return json.dumps(payload, default=str)


def _json_sink(message: loguru.Message) -> None:
    # Resolve trace ids through the Sentry owner file so this file never imports
    # sentry_sdk (one owner per SDK).
    from mcr_generation.app.utils.sentry_context import current_trace_ids

    trace_id, span_id = current_trace_ids()
    sys.stderr.write(_serialize_record(message.record, trace_id, span_id) + "\n")


def create_loguru_handler() -> None:
    if log_settings.JSON_LOGS:
        logger.add(_json_sink, level=log_settings.LEVEL, filter=loguru_filter)
        return
    logger.add(
        sys.stderr,
        format=get_log_format(),
        level=log_settings.LEVEL,
        filter=loguru_filter,
        colorize=log_settings.COLORIZE,
    )


def redirect_python_logging_to_loguru() -> None:
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.DEBUG)


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
