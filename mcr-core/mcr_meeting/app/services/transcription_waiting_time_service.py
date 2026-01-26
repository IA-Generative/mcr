import math
from datetime import datetime, timezone

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

    @staticmethod
    def get_meeting_remaining_waiting_time_minutes(meeting_id: int) -> int:
        """
        Get the remaining waiting time for a specific meeting in minutes.
        Based on the meeting's estimated end date minus current time.
        """
        meeting_transition_record = find_transition_record_by_meeting_and_status(
            meeting_id,
            MeetingStatus.TRANSCRIPTION_PENDING,
        )
        if not meeting_transition_record:
            raise ValueError(
                "Meeting transition record with ID {} not found".format(meeting_id)
            )

        predicted_date_of_next_transition = (
            meeting_transition_record.predicted_date_of_next_transition
        )
        if not predicted_date_of_next_transition:
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

        return remaining_minutes

    @staticmethod
    def estimate_current_wait_time_minutes() -> int:
        """
        Get the estimated waiting time for new meetings joining the transcription queue.
        Based on the total number of pending meetings and average processing time.

        Formula : Floor(N / parallel_pods_count) * average_transcription_time

        Returns:
            The waiting time in minutes
        """
        total_pending_meetings_count = count_pending_meetings()

        slots_needed = math.floor(
            total_pending_meetings_count
            / transcription_waiting_time_settings.PARALLEL_PODS_COUNT
        )

        current_waiting_time_minutes = (
            slots_needed
            * transcription_waiting_time_settings.AVERAGE_TRANSCRIPTION_TIME_MINUTES
        ) + int(transcription_waiting_time_settings.AVERAGE_MEETING_DURATION_HOURS * 60)

        return current_waiting_time_minutes

    @classmethod
    def estimate_transcription_duration_minutes(cls, meeting_id: int) -> int:
        meeting = get_meeting_by_id(meeting_id=meeting_id)

        if meeting.duration_minutes is not None:
            duration = meeting.duration_minutes
        else:
            duration = cls.estimate_default_meeting_duration()

        return (
            duration // transcription_waiting_time_settings.AVERAGE_TRANSCRIPTION_SPEED
        )

    def estimate_default_meeting_duration() -> int:
        duration_hour = int(
            transcription_waiting_time_settings.AVERAGE_MEETING_DURATION_HOURS
        )
        return duration_hour * 60
