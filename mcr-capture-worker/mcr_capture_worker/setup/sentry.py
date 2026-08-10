import os
from collections.abc import Iterator
from contextlib import contextmanager

import sentry_sdk
from loguru import logger
from sentry_sdk.tracing import Span

from mcr_capture_worker.settings.settings import ApiSettings


def setup_sentry() -> None:
    try:
        sentry_sdk.init(
            dsn=os.environ.get("SENTRY_CAPTURE_DSN"),
            send_default_pii=True,
            traces_sample_rate=0.2,
            environment=os.environ.get("ENV_MODE"),
            ignore_errors=[],
            # httpx is auto-instrumented, so scope trace propagation to core to
            # avoid leaking the trace onto the bot's third-party requests.
            trace_propagation_targets=[ApiSettings().CORE_SERVICE_BASE_URL],
        )
        logger.info("Sentry initialized")
    except Exception as e:
        logger.warning("Sentry initialization failed, continuing without it: {}", e)


@contextmanager
def transaction(op: str, name: str, **data: object) -> Iterator[Span]:
    # The bot runs outside any request/task, so it has no auto-transaction to
    # hang spans off. This opens one per capture; spans are dropped otherwise.
    with sentry_sdk.start_transaction(op=op, name=name) as txn:
        for key, value in data.items():
            txn.set_data(key, value)
        yield txn


@contextmanager
def span(op: str, name: str, **data: object) -> Iterator[Span]:
    with sentry_sdk.start_span(op=op, name=name) as current_span:
        for key, value in data.items():
            current_span.set_data(key, value)
        yield current_span


def capture_exception(error: Exception) -> None:
    sentry_sdk.capture_exception(error)
