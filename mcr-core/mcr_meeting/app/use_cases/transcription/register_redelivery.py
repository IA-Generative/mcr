from loguru import logger

from mcr_meeting.app.configs.base import CelerySettings
from mcr_meeting.app.exceptions.exceptions import TranscriptionAttemptsExhaustedError
from mcr_meeting.app.infrastructure.redis import increment_transcription_attempt

_settings = CelerySettings()


def register_redelivery(
    task_id: str, meeting_id: int, task_name: str, *, redelivered: bool
) -> None:
    if not redelivered:
        return
    try:
        attempt = increment_transcription_attempt(task_id) + 1
    except Exception:
        logger.exception(
            "Could not count redelivery of task {} for meeting {}", task_id, meeting_id
        )
        return
    logger.warning(
        "Task {} ({}) for meeting {} redelivered: attempt #{}/{}",
        task_name,
        task_id,
        meeting_id,
        attempt,
        _settings.TRANSCRIPTION_MAX_ATTEMPTS,
    )
    if attempt > _settings.TRANSCRIPTION_MAX_ATTEMPTS:
        raise TranscriptionAttemptsExhaustedError(
            f"Meeting {meeting_id}: task {task_name} exhausted its "
            f"{_settings.TRANSCRIPTION_MAX_ATTEMPTS} attempts"
        )
