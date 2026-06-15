from datetime import datetime, timezone

from mcr_meeting.app.db import deliverable_repository, meeting_repository
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain import deliverable_transitions, meeting_transitions
from mcr_meeting.app.models.deliverable_model import Deliverable
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord


def mark_deliverable_failure(deliverable_id: int) -> Deliverable:
    deliverable = deliverable_repository.get_by_id(deliverable_id)
    meeting = meeting_repository.get_meeting_by_id(deliverable.meeting_id)

    deliverable_transitions.mark_failed(deliverable)
    meeting_transitions.fail_report(meeting)

    with UnitOfWork():
        deliverable_repository.save_deliverable(deliverable)
        meeting_repository.update_meeting(meeting)

        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=datetime.now(timezone.utc),
                status=meeting.status,
            )
        )

    return deliverable
