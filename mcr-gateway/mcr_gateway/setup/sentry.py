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


def tag_sentry_request_id(request_id: str) -> None:
    # A no-op when Sentry is not initialized (e.g. tests), so callers stay simple.
    sentry_sdk.set_tag("request_id", request_id)


def current_trace_ids() -> tuple[str | None, str | None]:
    # Read the active trace/span so each JSON log line can be joined to its
    # Sentry trace in Grafana. Kept here because touching sentry_sdk is this
    # file's job (one owner per SDK); logger.py consumes this rather than
    # importing the SDK. Uses the propagation context, so it resolves even
    # between spans (e.g. a request handler outside any child span).
    traceparent = sentry_sdk.get_traceparent()
    if not traceparent:
        return None, None
    trace_id, _, rest = traceparent.partition("-")
    span_id = rest.partition("-")[0] or None
    return (trace_id or None), span_id
