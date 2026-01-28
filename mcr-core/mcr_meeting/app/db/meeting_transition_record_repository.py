from sqlalchemy import select

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models.meeting_model import Meeting
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord


def save_meeting_transition_record(
    transition_record: MeetingTransitionRecord,
) -> MeetingTransitionRecord:
    """
    Save a meeting transition record to the database.

    Args:
        transition_record: The transition record to save

    Returns:
        MeetingTransitionRecord: The saved transition record

    Raises:
        NotSavedException: If the record could not be saved
    """
    db = get_db_session_ctx()
    db.add(transition_record)
    return transition_record


def find_current_transition_record_for_meeting(
    meeting_id: int,
) -> MeetingTransitionRecord:
    """
    Get the last meeting transition record for the meeting with if meeting_id and status.
    """
    db = get_db_session_ctx()

    current_meeting_status = (
        select(Meeting.status).where(Meeting.id == meeting_id).scalar_subquery()
    )

    meeting_transition_record = (
        db.query(MeetingTransitionRecord)
        .filter(
            MeetingTransitionRecord.meeting_id == meeting_id,
            MeetingTransitionRecord.status == current_meeting_status,
        )
        .order_by(MeetingTransitionRecord.id.desc())
        .first()
    )

    if not meeting_transition_record:
        raise NotFoundException(
            "Meeting transition record with ID {} not found".format(meeting_id)
        )
    return meeting_transition_record
