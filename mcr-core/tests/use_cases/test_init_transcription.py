from unittest.mock import Mock, call

import pytest
from pytest_mock import MockerFixture
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


@pytest.fixture(autouse=True)
def structural_split_flag_off(mocker: MockerFixture) -> Mock:
    """Keep the flag read away from a real Unleash client; tests that exercise
    the split pipeline re-patch it to True."""
    return mocker.patch(
        "mcr_meeting.app.use_cases.init_transcription.is_enabled",
        return_value=False,
    )


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


def test_init_transcription_enqueues_chain_when_split_enabled(
    mock_celery_producer_app: Mock,
    structural_split_flag_off: Mock,
    mocker: MockerFixture,
) -> None:
    structural_split_flag_off.return_value = True
    chain_mock = mocker.patch("mcr_meeting.app.infrastructure.celery.chain")
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    result = init_transcription(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_PENDING
    args = [meeting.id, str(meeting.owner.keycloak_uuid)]
    # immutable=True obligatoire : en chain, un maillon mutable reçoit le
    # retour du précédent préfixé à ses args → TypeError sur nos tasks à 2 args.
    mock_celery_producer_app.signature.assert_has_calls(
        [
            call(MCRTranscriptionTasks.DIARIZE, args=args, immutable=True),
            call(MCRTranscriptionTasks.TRANSCRIBE_CHUNKS, args=args, immutable=True),
            call(
                MCRTranscriptionTasks.FINALIZE_TRANSCRIPTION,
                args=args,
                immutable=True,
            ),
        ]
    )
    chain_mock.return_value.apply_async.assert_called_once()
    mock_celery_producer_app.send_task.assert_not_called()


def test_init_transcription_falls_back_to_legacy_when_flag_unreadable(
    mock_celery_producer_app: Mock,
    structural_split_flag_off: Mock,
) -> None:
    structural_split_flag_off.side_effect = Exception("unleash down")
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    init_transcription(meeting_id=meeting.id)

    mock_celery_producer_app.send_task.assert_called_once_with(
        MCRTranscriptionTasks.TRANSCRIBE,
        args=[meeting.id, str(meeting.owner.keycloak_uuid)],
    )


def test_init_transcription_rolls_back_on_pipeline_broker_failure(
    mock_celery_producer_app: Mock,
    structural_split_flag_off: Mock,
    mocker: MockerFixture,
    db_session: Session,
) -> None:
    structural_split_flag_off.return_value = True
    chain_mock = mocker.patch("mcr_meeting.app.infrastructure.celery.chain")
    chain_mock.return_value.apply_async.side_effect = Exception("broker down")
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(TaskCreationException):
        init_transcription(meeting_id=meeting.id)

    assert _pending_records(meeting.id) == []


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
