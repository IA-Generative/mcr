import pytest

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.use_cases.fail_transcription import fail_transcription
from tests.factories import MeetingFactory


def _failed_records(meeting_id: int) -> list[MeetingTransitionRecord]:
    return list(
        get_db_session_ctx()
        .query(MeetingTransitionRecord)
        .filter(
            MeetingTransitionRecord.meeting_id == meeting_id,
            MeetingTransitionRecord.status == MeetingStatus.TRANSCRIPTION_FAILED,
        )
        .all()
    )


def test_fail_transcription_marks_status_failed() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    result = fail_transcription(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_FAILED


def test_fail_transcription_records_transition() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )

    fail_transcription(meeting_id=meeting.id)

    assert len(_failed_records(meeting.id)) == 1


def test_fail_transcription_rejects_illegal_transition() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(ValueError):
        fail_transcription(meeting_id=meeting.id)
