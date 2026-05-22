import math

from mcr_meeting.app.configs.base import TranscriptionWaitingTimeSettings
from mcr_meeting.app.db.meeting_repository import (
    count_pending_meetings,
    get_meeting_by_id,
)

transcription_wait_time_settings = TranscriptionWaitingTimeSettings()


class TranscriptionQueueEstimationService:
    """
    Service to calculate the estimated wait time for a meeting in the transcription queue.

    Calculate the wait time based on:
    - The number of meetings in TRANSCRIPTION_PENDING scheduled before the current meeting
    - The number of transcription pods in parallel (14)
    - The average transcription time per meeting (12 minutes)
    """

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
