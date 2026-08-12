import os

import sentry_sdk
from loguru import logger

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
