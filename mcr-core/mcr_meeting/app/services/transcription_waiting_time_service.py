import math
from datetime import datetime, timezone

from mcr_meeting.app.configs.base import TranscriptionWaitingTimeSettings
from mcr_meeting.app.db.meeting_repository import (
    count_pending_meetings,
    get_meeting_by_id,
)
from mcr_meeting.app.db.meeting_transition_record_repository import (
    find_current_transition_record_for_meeting,
)
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord

transcription_wait_time_settings = TranscriptionWaitingTimeSettings()


class TranscriptionQueueEstimationService:
    """
    Service to calculate the estimated wait time for a meeting in the transcription queue.

    Calculate the wait time based on:
    - The number of meetings in TRANSCRIPTION_PENDING scheduled before the current meeting
    - The number of transcription pods in parallel (14)
    - The average transcription time per meeting (12 minutes)
    """

    @classmethod
    def get_meeting_remaining_wait_time_minutes(cls, meeting_id: int) -> int:
        """
        Get the remaining wait time for a specific meeting in minutes.
        Based on the meeting's estimated end date minus current time.
        """
        meeting_transition_record = find_current_transition_record_for_meeting(
            meeting_id
        )

        predicted_wait_time_minutes = (
            cls.calculate_remaining_wait_time_from_transition_record(
                meeting_transition_record=meeting_transition_record
            )
        )

        return predicted_wait_time_minutes

    @staticmethod
    def estimate_current_wait_time_minutes() -> int:
        """
        Get the estimated wait time for new meetings joining the transcription queue.
        Based on the total number of pending meetings and average processing time.

        Formula : Floor(N / parallel_pods_count) * average_transcription_time

        Returns:
            The wait time in minutes
        """
        total_pending_meetings_count = count_pending_meetings()

        slots_needed = math.floor(
            total_pending_meetings_count
            / transcription_wait_time_settings.PARALLEL_PODS_COUNT
        )

        current_wait_time_minutes = (
            slots_needed
            * transcription_wait_time_settings.AVERAGE_TRANSCRIPTION_TIME_MINUTES
        )

        return current_wait_time_minutes

    @classmethod
    def estimate_transcription_duration_minutes(cls, meeting_id: int) -> int:
        meeting = get_meeting_by_id(meeting_id=meeting_id)

        if meeting.duration_minutes is not None:
            duration = meeting.duration_minutes
        else:
            duration = cls.estimate_default_meeting_duration()

        return duration // transcription_wait_time_settings.AVERAGE_TRANSCRIPTION_SPEED

    @staticmethod
    def estimate_default_meeting_duration() -> int:
        duration_hour = int(
            transcription_wait_time_settings.AVERAGE_MEETING_DURATION_HOURS
        )
        return duration_hour * 60

    @staticmethod
    def calculate_remaining_wait_time_from_transition_record(
        meeting_transition_record: MeetingTransitionRecord,
    ) -> int:
        predicted_date = meeting_transition_record.predicted_date_of_next_transition

        if predicted_date is None:
            raise ValueError(
                "Estimated end date is None for meeting {}".format(
                    meeting_transition_record.meeting_id
                )
            )

        if predicted_date.tzinfo is None:
            predicted_date = predicted_date.replace(tzinfo=timezone.utc)
        else:
            predicted_date = predicted_date.astimezone(timezone.utc)

        current_utc_time = datetime.now(timezone.utc)
        delta_seconds = (predicted_date - current_utc_time).total_seconds()
        predicted_wait_time_minutes = max(0, int(delta_seconds // 60))

        return predicted_wait_time_minutes
