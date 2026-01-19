from datetime import datetime, timedelta, timezone

from loguru import logger

from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
    update_meeting_transition_record_predicted_date_of_next_transition,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)


def create_transcription_transition_record_with_estimation(
    meeting_id: int, waiting_time_minutes: int
) -> MeetingTransitionRecord:
    """
    Create a transition record for the transcription with an estimated end time.

    Args:
        meeting_id: The ID of the meeting
        waiting_time_minutes: The estimated waiting time in minutes

    Returns:
        MeetingTransitionRecord: The created transition record
    """
    try:
        current_time = datetime.now(timezone.utc)

        predicted_date_of_next_transition = current_time + timedelta(
            minutes=waiting_time_minutes
        )

        transition_record = MeetingTransitionRecord(
            meeting_id=meeting_id,
            timestamp=current_time,
            predicted_date_of_next_transition=predicted_date_of_next_transition,
            status=MeetingStatus.TRANSCRIPTION_PENDING,
        )

        logger.info(
            "Creating transcription transition record for meeting {} with estimated waiting time: {} minutes",
            meeting_id,
            waiting_time_minutes,
        )
        with UnitOfWork():
            saved_record = save_meeting_transition_record(transition_record)
            return saved_record

    except Exception as e:
        logger.error(
            "Error creating transcription transition record for meeting {}: {}",
            meeting_id,
            e,
        )
        raise e


def update_meeting_transition_record_predicted_end_date_service(
    meeting_id: int,
) -> None:
    estimated_transcription_end_time = (
        TranscriptionQueueEstimationService.get_predicted_transcription_end_date()
    )

    with UnitOfWork():
        update_meeting_transition_record_predicted_date_of_next_transition(
            meeting_id=meeting_id,
            predicted_date_of_next_transition=estimated_transcription_end_time,
        )


def create_transition_record_service(
    meeting_id: int,
    next_status: MeetingStatus,
) -> None:
    if next_status == MeetingStatus.TRANSCRIPTION_PENDING:
        return

    try:
        current_time = datetime.now(timezone.utc)

        transition_record = MeetingTransitionRecord(
            meeting_id=meeting_id,
            timestamp=current_time,
            status=next_status,
        )

        logger.info(
            "Creating transcription transition record for meeting {} going into state : {}",
            meeting_id,
            next_status,
        )
        with UnitOfWork():
            save_meeting_transition_record(transition_record)

    except Exception as e:
        logger.error(
            "Error creating transcription transition record for meeting {}: {}",
            meeting_id,
            e,
        )
        raise e
