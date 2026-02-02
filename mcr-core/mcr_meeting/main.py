from contextlib import asynccontextmanager

import sentry_sdk
import uvicorn
from fastapi import FastAPI

from mcr_meeting.app.api.evaluation_router import router as evaluation_router
from mcr_meeting.app.api.feature_flag_router import router as feature_flag_router
from mcr_meeting.app.api.meeting.capture_bot_router import router as capture_bot_router
from mcr_meeting.app.api.meeting.capture_router import router as capture_router
from mcr_meeting.app.api.meeting.meeting_multipart_router import (
    router as meeting_multipart_router,
)
from mcr_meeting.app.api.meeting.meeting_router import router as meeting_router
from mcr_meeting.app.api.meeting.report_generation_router import (
    router as report_generation_router,
)
from mcr_meeting.app.api.meeting.transcription_router import (
    router as transcription_router,
)
from mcr_meeting.app.api.notification_router import router as notification_router
from mcr_meeting.app.api.user_router import router as user_router
from mcr_meeting.app.configs.base import SentrySettings, Settings
from mcr_meeting.app.exceptions.exception_handler import (
    mcr_exception_handler,
    value_error_handler,
)
from mcr_meeting.app.exceptions.exceptions import MCRException
from mcr_meeting.app.services.nats_manager import nats_manager
from mcr_meeting.app.services.websocket_manager import ws_manager
from mcr_meeting.setup.logger import setup_logging
from mcr_meeting.setup.request_id_middleware import AddRequestIdMiddleware

sentry_settings = SentrySettings()
setting = Settings()

if setting.ENV_MODE and setting.ENV_MODE != "test":
    sentry_sdk.init(
        dsn=sentry_settings.SENTRY_CORE_DSN,
        send_default_pii=sentry_settings.SEND_DEFAULT_PII,
        traces_sample_rate=sentry_settings.TRACES_SAMPLE_RATE,
        environment=setting.ENV_MODE,
        ignore_errors=[],
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):  # noqa: ARG001
    """Startup and shutdown events for NATS"""
    # Startup
    await nats_manager.connect()
    nats_manager.set_broadcast_callback(ws_manager.send_to_user)
    await nats_manager.start_consumer()

    yield

    # Shutdown
    await nats_manager.disconnect()


app = FastAPI(lifespan=lifespan)

setup_logging()

app.add_middleware(AddRequestIdMiddleware)
# Typing is ignored here because of the type-hint implementation on Starlette
# the handler typing excepts an Exception and can't be subclassed
# But at runtime, the handler will only get Exceptions of the type of the first parameter
app.add_exception_handler(MCRException, mcr_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(ValueError, value_error_handler)  # type: ignore[arg-type]

app.include_router(meeting_router)
app.include_router(capture_bot_router)
app.include_router(capture_router)
app.include_router(user_router)
app.include_router(evaluation_router)
app.include_router(transcription_router)
app.include_router(report_generation_router)
app.include_router(feature_flag_router)
app.include_router(meeting_multipart_router)
app.include_router(notification_router)

if __name__ == "__main__":
    uvicorn.run("main:app")
