from datetime import datetime, timezone

from pydantic import UUID4

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.db.meeting_repository import save_meeting
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.db.user_repository import get_user_by_keycloak_uuid
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.meeting_schema import MeetingCreate


def create_meeting(meeting_data: MeetingCreate, user_keycloak_uuid: UUID4) -> Meeting:
    user = get_user_by_keycloak_uuid(user_keycloak_uuid)
    _apply_initial_status(meeting_data)

    with UnitOfWork():
        meeting = save_meeting(user_id=user.id, meeting_data=meeting_data)
        get_db_session_ctx().flush()
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=datetime.now(timezone.utc),
                status=meeting_data.status,
            )
        )
        return meeting


def _apply_initial_status(meeting_data: MeetingCreate) -> None:
    match meeting_data.name_platform:
        case MeetingPlatforms.MCR_IMPORT:
            meeting_data.status = MeetingStatus.IMPORT_PENDING
        case MeetingPlatforms.MCR_RECORD:
            meeting_data.status = MeetingStatus.CAPTURE_IN_PROGRESS
            meeting_data.start_date = meeting_data.creation_date
        case _:
            meeting_data.status = MeetingStatus.NONE
