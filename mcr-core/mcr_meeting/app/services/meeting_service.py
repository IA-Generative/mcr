from datetime import datetime

from pydantic import UUID4

from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
)
from mcr_meeting.app.models import Meeting, MeetingStatus

from ..db.meeting_repository import (
    get_meeting_by_id,
    get_meeting_with_transcriptions,
    update_meeting,
)


def get_meeting_service(
    meeting_id: int, current_user_keycloak_uuid: UUID4 | None = None
) -> Meeting:
    """
    Service to retrieve a meeting by its ID.

    Args:
        meeting_id (int): The ID of the meeting to retrieve.

    Returns:
        Meeting: The meeting object with the specified ID, or None if not found.
    """

    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)

    if (
        current_user_keycloak_uuid is not None
        and meeting.owner.keycloak_uuid != current_user_keycloak_uuid
    ):
        raise ForbiddenAccessException("Meeting is owned by a different user")

    return meeting


def update_meeting_status(meeting: Meeting, meeting_status: MeetingStatus) -> Meeting:
    meeting.status = meeting_status
    return update_meeting(meeting)


def get_meeting_with_transcriptions_service(
    meeting_id: int, current_user_keycloak_uuid: UUID4
) -> Meeting:
    """
    Service to retrieve the Transcription and transform it to DOCX format by meeting ID.

    Args:
        meeting_id (int): The ID of the meeting to retrieve.

    Returns:
        list[Meeting]: A list of meeting objects belonging to the specified user.
    """
    meeting = get_meeting_with_transcriptions(meeting_id)

    if meeting.owner.keycloak_uuid != current_user_keycloak_uuid:
        raise ForbiddenAccessException("Meeting is owned by a different user")

    return meeting


def set_meeting_transcription_filename_and_update_status(
    meeting_id: int, filename: str
) -> None:
    meeting = get_meeting_by_id(meeting_id=meeting_id)
    meeting.transcription_filename = filename

    update_meeting(meeting)


def set_meeting_report_filename(meeting_id: int, filename: str) -> None:
    meeting = get_meeting_by_id(meeting_id=meeting_id)
    meeting.report_filename = filename
    update_meeting(meeting)


def update_meeting_start_date(meeting: Meeting, start_date: datetime) -> Meeting:
    meeting.start_date = start_date
    return update_meeting(meeting)


def update_meeting_end_date(meeting: Meeting, end_date: datetime) -> Meeting:
    meeting.end_date = end_date
    return update_meeting(meeting)
