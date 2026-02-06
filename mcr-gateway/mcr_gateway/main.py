from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcr_gateway.app.api import (
    authentification_router,
    lookup_router,
    meeting_multipart_router,
    meeting_router,
    notification_router,
    transcription_router,
)
from mcr_gateway.setup.logger import setup_logging
from mcr_gateway.setup.request_id_middleware import AddRequestIdMiddleware

app = FastAPI()

origins = ["http://localhost", "http://localhost:8000"]


setup_logging()

app.add_middleware(AddRequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(authentification_router.router, prefix="/api/auth")
app.include_router(meeting_router.router, prefix="/api")
app.include_router(lookup_router.router, prefix="/api")
app.include_router(transcription_router.router, prefix="/api")
app.include_router(meeting_multipart_router.router, prefix="/api")
app.include_router(notification_router.router, prefix="/api")
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
