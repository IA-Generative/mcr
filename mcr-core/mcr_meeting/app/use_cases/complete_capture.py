from datetime import datetime, timezone

from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.db.meeting_repository import update_meeting as update_meeting_in_db
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.domain.meeting_transitions import (
    complete_capture as apply_complete_capture,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord


def complete_capture(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    """Mark the capture of a meeting as complete.

    Transitions the meeting to ``CAPTURE_DONE``, stamps its end date and records
    the transition.
    """
    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)
    apply_complete_capture(meeting)

    with UnitOfWork():
        meeting.end_date = datetime.now(timezone.utc)
        update_meeting_in_db(meeting)
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=datetime.now(timezone.utc),
                status=meeting.status,
            )
        )

    return meeting
