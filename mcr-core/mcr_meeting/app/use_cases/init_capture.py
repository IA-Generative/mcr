from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.db.meeting_repository import update_meeting as update_meeting_in_db
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.domain.meeting_transitions import (
    init_capture as apply_init_capture,
)
from mcr_meeting.app.models import Meeting


def init_capture(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    """Initialise the capture for a meeting.

    Transitions the meeting to ``CAPTURE_PENDING``. The transition record is
    written by the state machine's ``after_transition`` hook.
    """
    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)
    apply_init_capture(meeting)

    with UnitOfWork():
        update_meeting_in_db(meeting)

    return meeting
