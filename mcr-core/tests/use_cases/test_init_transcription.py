from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import TaskCreationException
from mcr_meeting.app.models.meeting_model import (
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.celery_types import MCRTranscriptionTasks
from mcr_meeting.app.use_cases.init_transcription import init_transcription
from tests.factories import MeetingFactory


def _pending_records(meeting_id: int) -> list[MeetingTransitionRecord]:
    return list(
        get_db_session_ctx()
        .query(MeetingTransitionRecord)
        .filter(
            MeetingTransitionRecord.meeting_id == meeting_id,
            MeetingTransitionRecord.status == MeetingStatus.TRANSCRIPTION_PENDING,
        )
        .all()
    )


def test_init_transcription_queues_task_and_promotes_status(
    mock_celery_producer_app: Mock,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    result = init_transcription(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_PENDING
    mock_celery_producer_app.send_task.assert_called_once_with(
        MCRTranscriptionTasks.TRANSCRIBE,
        args=[meeting.id, str(meeting.owner.keycloak_uuid)],
    )


def test_init_transcription_records_predicted_pending_transition(
    mock_celery_producer_app: Mock,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    init_transcription(meeting_id=meeting.id)

    records = _pending_records(meeting.id)
    assert len(records) == 1
    assert records[0].predicted_date_of_next_transition is not None


def test_init_transcription_stamps_end_date_for_record_meetings(
    mock_celery_producer_app: Mock,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.MCR_RECORD,
    )

    result = init_transcription(meeting_id=meeting.id)

    assert result.end_date is not None


def test_init_transcription_rolls_back_on_broker_failure(
    mock_celery_producer_app: Mock,
    db_session: Session,
) -> None:
    mock_celery_producer_app.send_task.side_effect = Exception("broker down")
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(TaskCreationException):
        init_transcription(meeting_id=meeting.id)

    assert _pending_records(meeting.id) == []
    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.TRANSCRIPTION_PENDING


def test_init_transcription_rejects_illegal_transition(
    mock_celery_producer_app: Mock,
) -> None:
    meeting: Meeting = MeetingFactory.create(
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(ValueError):
        init_transcription(meeting_id=meeting.id)

    mock_celery_producer_app.send_task.assert_not_called()
