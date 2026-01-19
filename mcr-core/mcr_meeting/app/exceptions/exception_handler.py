"""
Exception handler for converting custom exceptions to HTTP responses.
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
    InvalidAudioFileError,
    MCRException,
    MeetingMultipartException,
    NotFoundException,
    NotSavedException,
    TaskCreationException,
)

# Mapping of exception types to status codes
EXCEPTION_STATUS_MAP = {
    InvalidAudioFileError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    NotFoundException: status.HTTP_404_NOT_FOUND,
    NotSavedException: status.HTTP_500_INTERNAL_SERVER_ERROR,
    TaskCreationException: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ForbiddenAccessException: status.HTTP_403_FORBIDDEN,
    MeetingMultipartException: status.HTTP_400_BAD_REQUEST,
}


async def mcr_exception_handler(request: Request, exc: MCRException) -> JSONResponse:
    """
    Handle MCRException exceptions and convert them to HTTP responses.

    Args:
        request: The FastAPI request object
        exc: The exception

    Returns:
        JSONResponse with appropriate status code and error message
    """
    status_code = EXCEPTION_STATUS_MAP.get(
        type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


async def value_error_handler(request: Request, exc: ValueError) -> None:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
    )
