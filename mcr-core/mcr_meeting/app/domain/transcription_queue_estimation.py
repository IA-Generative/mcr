"""Pure estimation of transcription queue waiting times.

No I/O lives here: the caller reads the pending-meeting count and the meeting
duration from the database and feeds them in. The numbers below come from the
``TranscriptionWaitingTimeSettings`` configuration.
"""

import math

from mcr_meeting.app.configs.base import TranscriptionWaitingTimeSettings

transcription_wait_time_settings = TranscriptionWaitingTimeSettings()


def estimate_wait_time_minutes(pending_meetings_count: int) -> int:
    """Estimate how long a meeting joining the queue now will wait before it is
    picked up.

    Formula: ``floor(N / parallel_pods_count) * average_transcription_time``.
    """
    slots_needed = math.floor(
        pending_meetings_count / transcription_wait_time_settings.PARALLEL_PODS_COUNT
    )

    return (
        slots_needed
        * transcription_wait_time_settings.AVERAGE_TRANSCRIPTION_TIME_MINUTES
    )


def estimate_transcription_duration_minutes(duration_minutes: int | None) -> int:
    """Estimate how long the transcription of a meeting will take, based on its
    recorded duration (falling back to the configured average when unknown)."""
    duration = (
        duration_minutes
        if duration_minutes is not None
        else default_meeting_duration_minutes()
    )

    return duration // transcription_wait_time_settings.AVERAGE_TRANSCRIPTION_SPEED


def default_meeting_duration_minutes() -> int:
    duration_hours = int(
        transcription_wait_time_settings.AVERAGE_MEETING_DURATION_HOURS
    )
    return duration_hours * 60
