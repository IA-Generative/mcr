from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.models.meeting_model import MeetingStatus
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


def find_transition_record_by_meeting_and_status(
    meeting_id: int,
    status: MeetingStatus,
) -> MeetingTransitionRecord | None:
    """
    Get a meeting transition record by meeting ID and status.
    """
    db = get_db_session_ctx()
    return (
        db.query(MeetingTransitionRecord)
        .filter(
            MeetingTransitionRecord.meeting_id == meeting_id,
            MeetingTransitionRecord.status == status,
        )
        .first()
    )
