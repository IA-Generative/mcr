import math
from datetime import datetime, timedelta, timezone

from loguru import logger

from mcr_meeting.app.configs.base import TranscriptionWaitingTimeSettings
from mcr_meeting.app.db.meeting_repository import (
    count_pending_meetings,
    get_meeting_by_id,
)
from mcr_meeting.app.db.meeting_transition_record_repository import (
    find_transition_record_by_meeting_and_status,
)
from mcr_meeting.app.models.meeting_model import MeetingStatus

transcription_waiting_time_settings = TranscriptionWaitingTimeSettings()


class TranscriptionQueueEstimationService:
    """
    Service to calculate the estimated waiting time for a meeting in the transcription queue.

    Calculate the waiting time based on:
    - The number of meetings in TRANSCRIPTION_PENDING scheduled before the current meeting
    - The number of transcription pods in parallel (14)
    - The average transcription time per meeting (12 minutes)
    """

    @classmethod
    def _calculate_waiting_time_from_count(cls, pending_meetings_count: int) -> int:
        """
        Calculate the waiting time based on the number of meetings in pending.

        Formula : Floor(N / parallel_pods_count) * average_transcription_time

        Args:
            pending_meetings_count: Number of meetings in pending

        Returns:
            The waiting time in minutes
        """
        slots_needed = (
            pending_meetings_count
            / transcription_waiting_time_settings.PARALLEL_PODS_COUNT
        )

        waiting_time_minutes = (
            math.floor(slots_needed)
            * transcription_waiting_time_settings.AVERAGE_TRANSCRIPTION_TIME_MINUTES
        ) + int(transcription_waiting_time_settings.AVERAGE_MEETING_DURATION_HOURS * 60)

        return waiting_time_minutes

    @classmethod
    def get_meeting_transcription_waiting_time_minutes(cls, meeting_id: int) -> int:
        """
        Utility function to get the waiting time for a meeting.

        Args:
            meeting_id: The ID of the meeting

        Returns:
            The estimated waiting time in minutes
        """
        try:
            current_meeting = get_meeting_by_id(meeting_id)
            if not current_meeting:
                logger.warning("Meeting with ID {} not found", meeting_id)
                raise ValueError("Meeting with ID {} not found".format(meeting_id))

            if not current_meeting.creation_date:
                logger.warning("Meeting {} has no creation_date", meeting_id)
                raise ValueError("Meeting {} has no creation_date".format(meeting_id))

            return cls.get_queue_estimated_waiting_time_minutes()

        except Exception as e:
            logger.error(
                "Error calculating waiting time for meeting {}: {}", meeting_id, e
            )
            raise

    @classmethod
    def get_meeting_remaining_waiting_time_minutes(cls, meeting_id: int) -> int:
        """
        Get the remaining waiting time for a specific meeting in minutes.
        Based on the meeting's estimated end date minus current time.
        """
        meeting_transition_record = find_transition_record_by_meeting_and_status(
            meeting_id,
            MeetingStatus.TRANSCRIPTION_PENDING,
        )
        if not meeting_transition_record:
            logger.warning("Meeting transition record with ID {} not found", meeting_id)
            raise ValueError(
                "Meeting transition record with ID {} not found".format(meeting_id)
            )

        predicted_date_of_next_transition = (
            meeting_transition_record.predicted_date_of_next_transition
        )
        if not predicted_date_of_next_transition:
            logger.warning("Estimated end date is None for meeting {}", meeting_id)
            raise ValueError(
                "Estimated end date is None for meeting {}".format(meeting_id)
            )

        if predicted_date_of_next_transition.tzinfo is None:
            predicted_date_of_next_transition = (
                predicted_date_of_next_transition.replace(tzinfo=timezone.utc)
            )
        else:
            predicted_date_of_next_transition = (
                predicted_date_of_next_transition.astimezone(timezone.utc)
            )

        current_utc_time = datetime.now(timezone.utc)
        delta_seconds = (
            predicted_date_of_next_transition - current_utc_time
        ).total_seconds()
        remaining_minutes = max(0, int(delta_seconds // 60))

        logger.info(
            "Remaining waiting time (minutes) for meeting {}: {}",
            meeting_id,
            remaining_minutes,
        )

        return remaining_minutes

    @classmethod
    def get_queue_estimated_waiting_time_minutes(cls) -> int:
        """
        Get the estimated waiting time for new meetings joining the transcription queue.
        Based on the total number of pending meetings and average processing time.
        """
        try:
            total_pending_meetings_count = count_pending_meetings()
            logger.info(
                "Total pending meetings count: {}", total_pending_meetings_count
            )

            current_waiting_time_minutes = cls._calculate_waiting_time_from_count(
                total_pending_meetings_count
            )

            logger.info(
                "Current waiting time: {} meetings pending, "
                "estimated waiting time: {} minutes",
                total_pending_meetings_count,
                current_waiting_time_minutes,
            )

            return current_waiting_time_minutes

        except Exception as e:
            logger.error("Error calculating current waiting time: {}", e)
            raise

    @classmethod
    def get_predicted_transcription_end_date(cls) -> datetime:
        current_date = datetime.now(timezone.utc)
        predicted_transcription_end_date = current_date + timedelta(
            minutes=transcription_waiting_time_settings.AVERAGE_MEETING_DURATION_HOURS
            * 60
        )

        return predicted_transcription_end_date
