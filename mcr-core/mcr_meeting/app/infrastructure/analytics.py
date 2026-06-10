"""Persistence of meeting transition records used for analytics and for the
predicted wait-times surfaced to users."""

from datetime import datetime, timedelta, timezone

from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord


def record_predicted_transition(
    meeting_id: int, status: MeetingStatus, waiting_time_minutes: int
) -> None:
    """Persist a transition record stamped with the predicted date of the next
    transition (``now + waiting_time_minutes``)."""
    current_time = datetime.now(timezone.utc)

    transition_record = MeetingTransitionRecord(
        meeting_id=meeting_id,
        timestamp=current_time,
        predicted_date_of_next_transition=current_time
        + timedelta(minutes=waiting_time_minutes),
        status=status,
    )

    with UnitOfWork():
        save_meeting_transition_record(transition_record)
