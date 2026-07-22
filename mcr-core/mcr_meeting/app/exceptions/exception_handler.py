"""
Exception handler for converting custom exceptions to HTTP responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from mcr_meeting.app.exceptions.exceptions import (
    BadRequestException,
    DataConflictException,
    DeliverableConcurrentlyCreatedException,
    DeliverableNotYetPendingError,
    DeliverableStateConflictException,
    ForbiddenAccessException,
    InvalidAudioFileError,
    InvalidDataException,
    InvalidEvaluationZipError,
    MCRException,
    MeetingMultipartException,
    MeetingStateConflictException,
    NotFoundException,
    SilentAudioError,
)

# Mapping of exception types to status codes
EXCEPTION_STATUS_MAP = {
    InvalidAudioFileError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    SilentAudioError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    InvalidDataException: status.HTTP_422_UNPROCESSABLE_ENTITY,
    DataConflictException: status.HTTP_409_CONFLICT,
    NotFoundException: status.HTTP_404_NOT_FOUND,
    ForbiddenAccessException: status.HTTP_404_NOT_FOUND,
    MeetingMultipartException: status.HTTP_400_BAD_REQUEST,
    BadRequestException: status.HTTP_400_BAD_REQUEST,
    InvalidEvaluationZipError: status.HTTP_400_BAD_REQUEST,
    DeliverableStateConflictException: status.HTTP_409_CONFLICT,
    DeliverableConcurrentlyCreatedException: status.HTTP_409_CONFLICT,
    MeetingStateConflictException: status.HTTP_409_CONFLICT,
    DeliverableNotYetPendingError: status.HTTP_425_TOO_EARLY,
}


async def mcr_exception_handler(request: Request, exc: MCRException) -> JSONResponse:
    status_code = EXCEPTION_STATUS_MAP.get(type(exc))
    if status_code is None:
        # Unmapped MCRExceptions are server faults, not anticipated client
        # outcomes: let them bubble to the catch-all so they are reported.
        raise exc

    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on {} {}", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error"},
    )
