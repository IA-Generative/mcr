from unittest.mock import Mock, call

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import (
    DeliverableConcurrentlyCreatedException,
    MeetingStateConflictException,
    TaskCreationException,
)
from mcr_meeting.app.infrastructure.unleash import FeatureFlag
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.celery_types import MCRTranscriptionTasks
from mcr_meeting.app.use_cases.init_transcription_and_minutes_report import (
    init_transcription_and_minutes_report,
)
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory
from tests.mocks.in_memory_feature_flags import InMemoryFeatureFlagClient


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


def _structured_minutes(meeting_id: int) -> list[Deliverable]:
    return list(
        get_db_session_ctx()
        .query(Deliverable)
        .filter(
            Deliverable.meeting_id == meeting_id,
            Deliverable.type == DeliverableType.STRUCTURED_MINUTES,
        )
        .all()
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


def test_init_transcription_and_minutes_report_queues_task_and_promotes_status(
    mock_celery_producer_app: Mock,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    result = init_transcription_and_minutes_report(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_PENDING
    mock_celery_producer_app.send_task.assert_called_once_with(
        MCRTranscriptionTasks.TRANSCRIBE,
        args=[meeting.id, str(meeting.owner.keycloak_uuid)],
        countdown=5,
        link_error=mock_celery_producer_app.signature.return_value,
    )


def test_init_transcription_and_minutes_report_records_predicted_pending_transition(
    mock_celery_producer_app: Mock,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    init_transcription_and_minutes_report(meeting_id=meeting.id)

    records = _pending_records(meeting.id)
    assert len(records) == 1
    assert records[0].predicted_date_of_next_transition is not None


def test_init_transcription_and_minutes_report_creates_pending_transcription_deliverable(
    mock_celery_producer_app: Mock,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    init_transcription_and_minutes_report(meeting_id=meeting.id)

    deliverables = _transcription_deliverables(meeting.id)
    assert len(deliverables) == 1
    assert deliverables[0].status == DeliverableStatus.PENDING


def test_init_transcription_and_minutes_report_rejects_when_active_deliverable_exists(
    mock_celery_producer_app: Mock,
) -> None:
    # init now only ever INSERTs; it never upserts. If an active deliverable
    # already exists (e.g. a stale FAILED one), the unique-active index rejects
    # the insert. Recovery from a failed transcription goes through the admin
    # requeue endpoint, not re-init.
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_FAILED,
        name_platform=MeetingPlatforms.COMU,
    )
    DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=DeliverableStatus.FAILED,
        external_url=None,
    )

    with pytest.raises(DeliverableConcurrentlyCreatedException):
        init_transcription_and_minutes_report(meeting_id=meeting.id)

    mock_celery_producer_app.send_task.assert_not_called()


def test_init_transcription_and_minutes_report_stamps_end_date_for_record_meetings(
    mock_celery_producer_app: Mock,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.MCR_RECORD,
    )

    result = init_transcription_and_minutes_report(meeting_id=meeting.id)

    assert result.end_date is not None


def test_init_transcription_and_minutes_report_rolls_back_on_broker_failure(
    mock_celery_producer_app: Mock,
    db_session: Session,
) -> None:
    mock_celery_producer_app.send_task.side_effect = Exception("broker down")
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(TaskCreationException):
        init_transcription_and_minutes_report(meeting_id=meeting.id)

    assert _pending_records(meeting.id) == []
    assert _transcription_deliverables(meeting.id) == []
    assert _structured_minutes(meeting.id) == []
    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.TRANSCRIPTION_PENDING


def test_init_transcription_and_minutes_report_enqueues_chain_when_split_enabled(
    mock_celery_producer_app: Mock,
    feature_flags: InMemoryFeatureFlagClient,
    mocker: MockerFixture,
) -> None:
    feature_flags.enable(FeatureFlag.STRUCTURAL_SPLIT_ENABLED)
    chain_mock = mocker.patch("mcr_meeting.app.infrastructure.celery.chain")
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    result = init_transcription_and_minutes_report(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_PENDING
    args = [meeting.id, str(meeting.owner.keycloak_uuid)]
    mock_celery_producer_app.signature.assert_has_calls(
        [
            call(MCRTranscriptionTasks.DIARIZE, args=args, immutable=True),
            call(MCRTranscriptionTasks.TRANSCRIBE_CHUNKS, args=args, immutable=True),
            call(
                MCRTranscriptionTasks.FINALIZE_TRANSCRIPTION,
                args=args,
                immutable=True,
            ),
            call(
                MCRTranscriptionTasks.MARK_TRANSCRIPTION_FAILED,
                args=args,
                immutable=True,
            ),
        ]
    )
    chain_mock.return_value.apply_async.assert_called_once_with(
        countdown=5,
        link_error=mock_celery_producer_app.signature.return_value,
    )
    mock_celery_producer_app.send_task.assert_not_called()


def test_init_transcription_and_minutes_report_falls_back_to_legacy_when_flag_unreadable(
    mock_celery_producer_app: Mock,
    feature_flags: InMemoryFeatureFlagClient,
) -> None:
    feature_flags.fail_with(Exception("unleash down"))
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    init_transcription_and_minutes_report(meeting_id=meeting.id)

    mock_celery_producer_app.send_task.assert_called_once_with(
        MCRTranscriptionTasks.TRANSCRIBE,
        args=[meeting.id, str(meeting.owner.keycloak_uuid)],
        countdown=5,
        link_error=mock_celery_producer_app.signature.return_value,
    )


def test_init_transcription_and_minutes_report_rolls_back_on_pipeline_broker_failure(
    mock_celery_producer_app: Mock,
    feature_flags: InMemoryFeatureFlagClient,
    mocker: MockerFixture,
    db_session: Session,
) -> None:
    feature_flags.enable(FeatureFlag.STRUCTURAL_SPLIT_ENABLED)
    chain_mock = mocker.patch("mcr_meeting.app.infrastructure.celery.chain")
    chain_mock.return_value.apply_async.side_effect = Exception("broker down")
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(TaskCreationException):
        init_transcription_and_minutes_report(meeting_id=meeting.id)

    assert _pending_records(meeting.id) == []


def test_init_transcription_and_minutes_report_rejects_illegal_transition(
    mock_celery_producer_app: Mock,
) -> None:
    meeting: Meeting = MeetingFactory.create(
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(MeetingStateConflictException):
        init_transcription_and_minutes_report(meeting_id=meeting.id)

    mock_celery_producer_app.send_task.assert_not_called()
    assert _transcription_deliverables(meeting.id) == []


def test_init_requests_default_structured_minutes(
    mock_celery_producer_app: Mock,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    init_transcription_and_minutes_report(meeting_id=meeting.id)

    reports = _structured_minutes(meeting.id)
    assert len(reports) == 1
    assert reports[0].status == DeliverableStatus.REQUESTED
    assert reports[0].custom_prompt is None
    # No dispatch at launch: only the transcription task is sent.
    mock_celery_producer_app.send_task.assert_called_once_with(
        MCRTranscriptionTasks.TRANSCRIBE,
        args=[meeting.id, str(meeting.owner.keycloak_uuid)],
        countdown=5,
        link_error=mock_celery_producer_app.signature.return_value,
    )


def test_init_does_not_duplicate_an_existing_structured_minutes(
    mock_celery_producer_app: Mock,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_DONE,
        name_platform=MeetingPlatforms.COMU,
    )
    existing = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.STRUCTURED_MINUTES,
        status=DeliverableStatus.REQUESTED,
    )

    init_transcription_and_minutes_report(meeting_id=meeting.id)

    reports = _structured_minutes(meeting.id)
    assert len(reports) == 1
    assert reports[0].id == existing.id
