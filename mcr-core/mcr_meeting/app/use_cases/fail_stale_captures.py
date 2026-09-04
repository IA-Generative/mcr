from datetime import datetime, timedelta, timezone

from loguru import logger

from mcr_meeting.app.configs.base import StaleCaptureSettings
from mcr_meeting.app.db.meeting_repository import (
    get_capture_meetings_stuck_since_before,
)
from mcr_meeting.app.db.meeting_repository import update_meeting as update_meeting_in_db
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.meeting_transitions import fail_stale_capture
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord

stale_capture_settings = StaleCaptureSettings()


def fail_stale_captures(now: datetime | None = None) -> list[Meeting]:
    """Fail every capture that outlived the maximum capture age.

    Covers captures whose worker died before stopping them, and browser
    recordings the user abandoned, so the meeting stops looking live forever.
    """
    now = now or datetime.now(timezone.utc)
    before = now - timedelta(hours=stale_capture_settings.STALE_CAPTURE_MAX_AGE_HOURS)
    stale_meetings = get_capture_meetings_stuck_since_before(before)

    for meeting in stale_meetings:
        previous_status = meeting.status
        fail_stale_capture(meeting)
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
            stale_capture_settings.STALE_CAPTURE_MAX_AGE_HOURS,
            meeting.status,
        )

    return stale_meetings
