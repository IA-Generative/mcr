from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import UUID4

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.services.meeting_transition_record_service import (
    create_transition_record_service,
)
from mcr_meeting.app.services.user_service import get_user_by_keycloak_uuid_service
from mcr_meeting.app.utils.db_utils import update_model

from ..db.meeting_repository import (
    get_meeting_by_id,
    get_meeting_with_transcriptions,
    get_meetings,
    save_meeting,
    update_meeting,
)
from ..schemas.meeting_schema import (
    MeetingCreate,
    MeetingUpdate,
)


def create_meeting_service(
    meeting_data: MeetingCreate, user_keycloak_uuid: UUID
) -> Meeting:
    """
    Service to create a new meeting.

    Args:
        meeting_data: The meeting object to be created.

    Returns:
        Meeting: The created meeting object with updated information (e.g., ID).
    """
    user = get_user_by_keycloak_uuid_service(user_keycloak_uuid)

    match meeting_data.name_platform:
        case "MCR_IMPORT":
            meeting_data.status = MeetingStatus.IMPORT_PENDING
        case "MCR_RECORD":
            meeting_data.status = MeetingStatus.CAPTURE_IN_PROGRESS
            meeting_data.start_date = meeting_data.creation_date
        case _:
            meeting_data.status = MeetingStatus.NONE

    with UnitOfWork():
        meeting = save_meeting(user_id=user.id, meeting_data=meeting_data)
        get_db_session_ctx().flush()
        create_transition_record_service(meeting.id, meeting_data.status)
        return meeting


def get_meeting_service(
    meeting_id: int, current_user_keycloak_uuid: Optional[UUID4] = None
) -> Meeting:
    """
    Service to retrieve a meeting by its ID.

    Args:
        meeting_id (int): The ID of the meeting to retrieve.

    Returns:
        Meeting: The meeting object with the specified ID, or None if not found.
    """

    meeting = get_meeting_by_id(meeting_id)

    if (
        current_user_keycloak_uuid is not None
        and meeting.owner.keycloak_uuid != current_user_keycloak_uuid
    ):
        raise ForbiddenAccessException("Meeting is owned by a different user")

    return meeting


def update_meeting_service(
    meeting_id: int, current_user_keycloak_uuid: UUID4, meeting_update: MeetingUpdate
) -> Meeting:
    """
    Service to update an existing meeting.

    Args:

        meeting_id (int): The ID of the meeting to update.
        meeting_update (MeetingUpdate): The Pydantic model containing the updated meeting data.

    Returns:
        Meeting: The updated meeting object, or None if no meeting was found.
    """

    with UnitOfWork():
        meeting = get_meeting_service(
            meeting_id=meeting_id, current_user_keycloak_uuid=current_user_keycloak_uuid
        )
        update_model(meeting, meeting_update)

        return update_meeting(meeting)


def update_meeting_status(meeting: Meeting, meeting_status: MeetingStatus) -> Meeting:
    meeting.status = meeting_status
    return update_meeting(meeting)


def get_meetings_service(
    user_keycloak_uuid: UUID, search: Optional[str]
) -> List[Meeting]:
    """
    Service pour récupérer une liste de réunions.

    Args:
        search (str): Terme de recherche optionnel pour filtrer les réunions.

    Returns:
        List[Meeting]: Liste des réunions correspondant aux critères.
    """
    user = get_user_by_keycloak_uuid_service(user_keycloak_uuid)

    return get_meetings(search=search, user_id=user.id)


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
