from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.db.meeting_repository import update_meeting as update_meeting_in_db
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.schemas.meeting_schema import MeetingUpdate
from mcr_meeting.app.utils.db_utils import patch_model


def update_meeting(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    user_keycloak_uuid: UUID4,
) -> Meeting:
    with UnitOfWork():
        meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
        authorize_meeting_access(meeting, user_keycloak_uuid)
        patch_model(meeting, meeting_update)
        return update_meeting_in_db(meeting)
