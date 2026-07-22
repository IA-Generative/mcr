import uvicorn
from fastapi import FastAPI

from mcr_meeting.app.api._shared.request_id_middleware import AddRequestIdMiddleware
from mcr_meeting.app.api.evaluation_router import router as evaluation_router
from mcr_meeting.app.api.feature_flag_router import router as feature_flag_router
from mcr_meeting.app.api.feedback_router import router as feedback_router
from mcr_meeting.app.api.lookup_router import router as lookup_router
from mcr_meeting.app.api.meeting.capture_bot_router import router as capture_bot_router
from mcr_meeting.app.api.meeting.capture_router import router as capture_router
from mcr_meeting.app.api.meeting.deliverable_router import (
    deliverables_router,
)
from mcr_meeting.app.api.meeting.deliverable_router import (
    meeting_scoped_router as deliverable_meeting_router,
)
from mcr_meeting.app.api.meeting.meeting_multipart_router import (
    router as meeting_multipart_router,
)
from mcr_meeting.app.api.meeting.meeting_router import router as meeting_router
from mcr_meeting.app.api.meeting.requeue_router import router as requeue_router
from mcr_meeting.app.api.meeting.transcription_router import (
    router as transcription_router,
)
from mcr_meeting.app.api.user_router import router as user_router
from mcr_meeting.app.exceptions.exception_handler import (
    mcr_exception_handler,
    unhandled_exception_handler,
)
from mcr_meeting.app.exceptions.exceptions import MCRException
from mcr_meeting.app.infrastructure.logger import setup_logging
from mcr_meeting.app.infrastructure.sentry import init_api_sentry

init_api_sentry()

app = FastAPI()

setup_logging()

app.add_middleware(AddRequestIdMiddleware)
# Typing is ignored here because of the type-hint implementation on Starlette
# the handler typing excepts an Exception and can't be subclassed
# But at runtime, the handler will only get Exceptions of the type of the first parameter
app.add_exception_handler(MCRException, mcr_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]

app.include_router(meeting_router)
app.include_router(lookup_router)
app.include_router(capture_bot_router)
app.include_router(capture_router)
app.include_router(user_router)
app.include_router(evaluation_router)
app.include_router(feature_flag_router)
app.include_router(meeting_multipart_router)
app.include_router(feedback_router)
app.include_router(deliverable_meeting_router)
app.include_router(deliverables_router)
app.include_router(transcription_router)
app.include_router(requeue_router)

if __name__ == "__main__":
    uvicorn.run("main:app")
