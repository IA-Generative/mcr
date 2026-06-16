import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.use_cases.start_transcription import start_transcription
from tests.factories import MeetingFactory


def _in_progress_records(meeting_id: int) -> list[MeetingTransitionRecord]:
    return list(
        get_db_session_ctx()
        .query(MeetingTransitionRecord)
        .filter(
            MeetingTransitionRecord.meeting_id == meeting_id,
            MeetingTransitionRecord.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        )
        .all()
    )


def test_start_transcription_promotes_status() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )

    result = start_transcription(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS


def test_start_transcription_records_predicted_transition() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )

    start_transcription(meeting_id=meeting.id)

    records = _in_progress_records(meeting.id)
    assert len(records) == 1
    assert records[0].predicted_date_of_next_transition is not None


def test_start_transcription_rejects_illegal_transition(db_session: Session) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(ValueError):
        start_transcription(meeting_id=meeting.id)

    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.CAPTURE_DONE
    assert _in_progress_records(meeting.id) == []
