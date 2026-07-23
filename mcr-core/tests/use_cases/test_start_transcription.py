import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import (
    MeetingStateConflictException,
    NotFoundException,
)
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.use_cases.start_transcription import start_transcription
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory


def _transcription_deliverables(meeting_id: int) -> list[Deliverable]:
    return list(
        get_db_session_ctx()
        .query(Deliverable)
        .filter(
            Deliverable.meeting_id == meeting_id,
            Deliverable.type == DeliverableType.TRANSCRIPTION,
        )
        .all()
    )


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


def _pending_transcription_deliverable(meeting: object) -> Deliverable:
    return DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=DeliverableStatus.PENDING,
        external_url=None,
    )


def test_start_transcription_promotes_status() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )
    _pending_transcription_deliverable(meeting)

    result = start_transcription(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS


def test_start_transcription_records_predicted_transition() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )
    _pending_transcription_deliverable(meeting)

    start_transcription(meeting_id=meeting.id)

    records = _in_progress_records(meeting.id)
    assert len(records) == 1
    assert records[0].predicted_date_of_next_transition is not None


def test_start_transcription_marks_deliverable_in_progress() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )
    pending_deliverable = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=DeliverableStatus.PENDING,
        external_url=None,
    )

    start_transcription(meeting_id=meeting.id)

    deliverables = _transcription_deliverables(meeting.id)
    assert len(deliverables) == 1
    assert deliverables[0].id == pending_deliverable.id
    assert deliverables[0].status == DeliverableStatus.IN_PROGRESS


def test_start_transcription_raises_when_deliverable_missing(
    db_session: Session,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(NotFoundException):
        start_transcription(meeting_id=meeting.id)

    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.TRANSCRIPTION_PENDING
    assert _transcription_deliverables(meeting.id) == []
    assert _in_progress_records(meeting.id) == []


def test_start_transcription_rejects_illegal_transition(db_session: Session) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(MeetingStateConflictException):
        start_transcription(meeting_id=meeting.id)

    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.CAPTURE_DONE
    assert _in_progress_records(meeting.id) == []
    assert _transcription_deliverables(meeting.id) == []
