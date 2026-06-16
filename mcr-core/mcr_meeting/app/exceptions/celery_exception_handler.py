"""
React to core HTTP responses for the transcription transitions.

Counterpart of exception_handler.py: the server maps business exceptions to HTTP
status codes; here the worker maps those status codes back to a control-flow
decision (end the task / log and continue / let it fail).
"""

from fastapi import status
from loguru import logger

from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException


def raise_for_core_status(status_code: int, meeting_id: int) -> bool:
    if status_code == status.HTTP_404_NOT_FOUND:
        raise MeetingDeletedException()
    if status_code == status.HTTP_409_CONFLICT:
        logger.warning(
            "Core returned 409 for meeting {}: already transitioned; continuing",
            meeting_id,
        )
        return True
    return False
