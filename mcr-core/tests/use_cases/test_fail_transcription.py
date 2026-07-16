import pytest

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import MeetingStateConflictException
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.use_cases.fail_transcription import fail_transcription
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


def test_fail_transcription_marks_deliverable_failed() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )
    early_deliverable = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=DeliverableStatus.IN_PROGRESS,
        external_url=None,
    )

    fail_transcription(meeting_id=meeting.id)

    deliverables = _transcription_deliverables(meeting.id)
    assert len(deliverables) == 1
    assert deliverables[0].id == early_deliverable.id
    assert deliverables[0].status == DeliverableStatus.FAILED


def test_fail_transcription_creates_failed_deliverable_when_missing() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    fail_transcription(meeting_id=meeting.id)

    deliverables = _transcription_deliverables(meeting.id)
    assert len(deliverables) == 1
    assert deliverables[0].status == DeliverableStatus.FAILED


def test_fail_transcription_silent_conflicts_when_transcription_already_done() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(MeetingStateConflictException):
        fail_transcription(meeting_id=meeting.id)

    assert _failed_records(meeting.id) == []


def test_fail_transcription_conflicts_on_illegal_transition() -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )
    available_deliverable = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=DeliverableStatus.AVAILABLE,
    )

    with pytest.raises(MeetingStateConflictException):
        fail_transcription(meeting_id=meeting.id)

    assert _failed_records(meeting.id) == []
    deliverables = _transcription_deliverables(meeting.id)
    assert len(deliverables) == 1
    assert deliverables[0].id == available_deliverable.id
    assert deliverables[0].status == DeliverableStatus.AVAILABLE
