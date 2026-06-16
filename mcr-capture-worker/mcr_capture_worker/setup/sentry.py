import os

import sentry_sdk
from loguru import logger


def setup_sentry() -> None:
    try:
        sentry_sdk.init(
            dsn=os.environ.get("SENTRY_CAPTURE_DSN"),
            send_default_pii=True,
            traces_sample_rate=0.2,
            environment=os.environ.get("ENV_MODE"),
            ignore_errors=[],
        )
        logger.info("Sentry initialized")
    except Exception as e:
        logger.warning("Sentry initialization failed, continuing without it: {}", e)
