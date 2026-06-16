import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.celery import CeleryIntegration

from mcr_meeting.app.configs.base import SentrySettings, Settings


def init_sentry() -> None:
    sentry_settings = SentrySettings()
    settings = Settings()

    try:
        sentry_sdk.init(
            dsn=sentry_settings.SENTRY_TRANSCRIPTION_DSN,
            send_default_pii=sentry_settings.SEND_DEFAULT_PII,
            traces_sample_rate=sentry_settings.TRACES_SAMPLE_RATE,
            environment=settings.ENV_MODE,
            ignore_errors=[],
            integrations=[CeleryIntegration()],
        )
    except Exception as e:
        logger.warning("Sentry initialization failed, continuing without it: {}", e)
