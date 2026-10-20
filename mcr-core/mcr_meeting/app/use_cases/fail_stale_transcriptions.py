from datetime import datetime, timedelta, timezone

from loguru import logger

from mcr_meeting.app.configs.base import StaleTranscriptionSettings
from mcr_meeting.app.db.meeting_repository import (
    get_transcription_meetings_stuck_since_before,
)
from mcr_meeting.app.db.meeting_repository import update_meeting as update_meeting_in_db
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.meeting_transitions import fail_transcription
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord

stale_transcription_settings = StaleTranscriptionSettings()


def fail_stale_transcriptions(now: datetime | None = None) -> list[Meeting]:
    now = now or datetime.now(timezone.utc)
    before = now - timedelta(
        hours=stale_transcription_settings.STALE_TRANSCRIPTION_MAX_AGE_HOURS
    )
    stale_meetings = get_transcription_meetings_stuck_since_before(before)

    for meeting in stale_meetings:
        previous_status = meeting.status
        fail_transcription(meeting)
        with UnitOfWork():
            update_meeting_in_db(meeting)
            save_meeting_transition_record(
                MeetingTransitionRecord(
                    meeting_id=meeting.id,
                    timestamp=now,
                    status=meeting.status,
                )
            )
        logger.warning(
            "Meeting {} stuck in {} for more than {}h -- marked {}",
            meeting.id,
            previous_status,
            stale_transcription_settings.STALE_TRANSCRIPTION_MAX_AGE_HOURS,
            meeting.status,
        )

    return stale_meetings
