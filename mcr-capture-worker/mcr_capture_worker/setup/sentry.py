import logging  # noqa: TID251
import os

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration


def _logging_integrations() -> list[Integration]:
    # A logged error is not a failure point: keep log records as breadcrumbs
    # (level=INFO) but never let them become Sentry events (event_level=None).
    # Real capture failures are reported explicitly via capture_exception.
    return [
        LoguruIntegration(event_level=None, level=logging.INFO),
        LoggingIntegration(event_level=None, level=logging.INFO),
    ]


def setup_sentry() -> None:
    try:
        sentry_sdk.init(
            dsn=os.environ.get("SENTRY_CAPTURE_DSN"),
            send_default_pii=True,
            traces_sample_rate=0.2,
            environment=os.environ.get("ENV_MODE"),
            ignore_errors=[],
            integrations=_logging_integrations(),
        )
        logger.info("Sentry initialized")
    except Exception as e:
        logger.warning("Sentry initialization failed, continuing without it: {}", e)
