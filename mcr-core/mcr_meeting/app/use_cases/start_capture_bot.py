from datetime import datetime, timezone

from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.db.meeting_repository import update_meeting as update_meeting_in_db
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.domain.meeting_transitions import assert_meeting_transition
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord


def start_capture_bot(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    """Record that the capture bot successfully connected to the meeting.

    Transitions the meeting to ``CAPTURE_IN_PROGRESS`` and stamps its start date.
    """
    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)
    assert_meeting_transition(meeting.status, MeetingStatus.CAPTURE_IN_PROGRESS)

    with UnitOfWork():
        meeting.status = MeetingStatus.CAPTURE_IN_PROGRESS
        meeting.start_date = datetime.now(timezone.utc)
        update_meeting_in_db(meeting)
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=datetime.now(timezone.utc),
                status=MeetingStatus.CAPTURE_IN_PROGRESS,
            )
        )

    return meeting
