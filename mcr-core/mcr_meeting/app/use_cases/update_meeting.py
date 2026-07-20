from pydantic import UUID4

from mcr_meeting.app.db import meeting_repository
from mcr_meeting.app.db.apply_dto import apply_dto_patch
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.schemas.meeting_schema import MeetingUpdate


def update_meeting(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    user_keycloak_uuid: UUID4,
) -> Meeting:
    meeting = meeting_repository.get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)

    with UnitOfWork():
        apply_dto_patch(meeting, meeting_update)
        return meeting_repository.update_meeting(meeting)
