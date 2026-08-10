import sentry_sdk
from loguru import logger

from mcr_gateway.app.configs.config import SentrySettings, Settings

settings = Settings()
sentry_settings = SentrySettings()


def setup_sentry() -> None:
    env_mode = settings.ENV_MODE
    if not env_mode or env_mode == "test":
        return
    try:
        sentry_sdk.init(
            dsn=sentry_settings.SENTRY_GATEWAY_DSN,
            send_default_pii=sentry_settings.SEND_DEFAULT_PII,
            traces_sample_rate=sentry_settings.TRACES_SAMPLE_RATE,
            environment=env_mode,
            ignore_errors=[],
        )
    except Exception as e:
        logger.warning("Sentry initialization failed, continuing without it: {}", e)


def tag_request_id(request_id: str) -> None:
    # A no-op when Sentry is not initialized (e.g. tests), so callers stay simple.
    sentry_sdk.set_tag("request_id", request_id)
