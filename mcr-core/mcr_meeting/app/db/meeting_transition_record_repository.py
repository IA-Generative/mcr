from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import NotSavedException
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


def update_meeting_transition_record_predicted_date_of_next_transition(
    meeting_id: int, predicted_date_of_next_transition: datetime
) -> MeetingTransitionRecord:
    """
    Update the estimated end date of a meeting transition record.

    Args:
        meeting_id: The ID of the meeting
        predicted_date_of_next_transition: The new estimated end date

    Returns:
        MeetingTransitionRecord: The updated transition record

    Raises:
        NotSavedException: If the record could not be updated
        ValueError: If the meeting transition record is not found
    """
    db = get_db_session_ctx()
    try:
        transition_record = find_transition_record_by_meeting_and_status(
            meeting_id,
            MeetingStatus.TRANSCRIPTION_PENDING,
        )

        if not transition_record:
            raise ValueError(
                f"Meeting transition record not found for meeting {meeting_id}"
            )

        transition_record.predicted_date_of_next_transition = (
            predicted_date_of_next_transition
        )
        return transition_record
    except SQLAlchemyError as update_error:
        db.rollback()
        raise NotSavedException(
            f"Could not update meeting transition record: {str(update_error)}"
        )
