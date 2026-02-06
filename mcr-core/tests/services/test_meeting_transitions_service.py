from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, Mock
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.configs.base import TranscriptionWaitingTimeSettings
from mcr_meeting.app.models.meeting_model import (
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.orchestrators import meeting_transitions_orchestrator as mts
from mcr_meeting.app.statemachine_actions import meeting_actions
from tests.factories import MeetingFactory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_keycloak_uuid(orchestrator_user: User) -> UUID:
    """Use the keycloak_uuid from the orchestrator_user fixture."""
    return orchestrator_user.keycloak_uuid


@pytest.fixture
def _mock_save_formatted_report(monkeypatch: Any) -> MagicMock:
    save_formatted_report_mock = MagicMock()

    monkeypatch.setattr(
        meeting_actions,
        "save_formatted_report",
        save_formatted_report_mock,
    )

    return save_formatted_report_mock


@pytest.fixture
def mock_send_email(monkeypatch: Any) -> MagicMock:
    """Mock email service to prevent actual emails during tests."""
    send_email_mock = MagicMock()

    monkeypatch.setattr(
        "mcr_meeting.app.services.send_email_service._send_email",
        send_email_mock,
    )

    return send_email_mock


# ---------------------------------------------------------------------------
# Tests – Capture
# ---------------------------------------------------------------------------


def test_init_capture(
    visio_meeting: Meeting,
    user_keycloak_uuid: UUID,
) -> None:
    """Test initializing capture transitions meeting to CAPTURE_PENDING."""
    result = mts.init_capture(
        meeting_id=visio_meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_PENDING


def test_start_capture(
    orchestrator_user: User,
    user_keycloak_uuid: UUID,
) -> None:
    """Test starting capture transitions meeting to CAPTURE_BOT_IS_CONNECTING."""
    meeting = MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.CAPTURE_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )

    result = mts.start_capture(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_BOT_IS_CONNECTING


def test_complete_capture(
    orchestrator_user: User,
    user_keycloak_uuid: UUID,
) -> None:
    """Test completing capture transitions meeting to CAPTURE_DONE."""
    meeting = MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    result = mts.complete_capture(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_DONE


def test_start_capture_bot(
    orchestrator_user: User,
    user_keycloak_uuid: UUID,
) -> None:
    """Test bot connection success transitions to CAPTURE_IN_PROGRESS."""
    meeting = MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.CAPTURE_BOT_IS_CONNECTING,
        name_platform=MeetingPlatforms.COMU,
    )

    result = mts.start_capture_bot(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_IN_PROGRESS


def test_fail_capture_bot(
    orchestrator_user: User,
    user_keycloak_uuid: UUID,
) -> None:
    """Test bot connection failure transitions to CAPTURE_BOT_CONNECTION_FAILED."""
    meeting = MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.CAPTURE_BOT_IS_CONNECTING,
        name_platform=MeetingPlatforms.COMU,
    )

    result = mts.fail_capture_bot(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_BOT_CONNECTION_FAILED


def test_fail_capture(
    orchestrator_user: User,
    user_keycloak_uuid: UUID,
) -> None:
    """Test capture failure transitions to CAPTURE_FAILED."""
    meeting = MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    result = mts.fail_capture(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_FAILED


def test_delete(
    orchestrator_user: User,
    user_keycloak_uuid: UUID,
) -> None:
    """Test meeting status to DELETED."""
    meeting = MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    result = mts.delete(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )
    assert result.status == MeetingStatus.DELETED
    
    
# ---------------------------------------------------------------------------
# Tests – Transcription
# ---------------------------------------------------------------------------


def test_init_transcription(
    mock_celery_producer_app: Mock,
    import_meeting: Meeting,
    user_keycloak_uuid: UUID,
) -> None:
    """Test initializing transcription transitions to TRANSCRIPTION_PENDING."""
    result = mts.init_transcription(
        meeting_id=import_meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.TRANSCRIPTION_PENDING


def test_start_transcription(db_session: Session) -> None:
    """Test starting transcription transitions to TRANSCRIPTION_IN_PROGRESS."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.MCR_IMPORT,
    )

    result = mts.start_transcription(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS


def test_start_transcription_creates_log_with_prediction() -> None:
    """Test that start_transcription creates exactly one transition log with prediction."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.MCR_IMPORT,
        with_dates=True,
    )

    result = mts.start_transcription(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS


def test_start_transcription_missing_start_date_uses_default_prediction(
    db_session: Session,
) -> None:
    """Test that start_transcription uses 1h default prediction when start_date is missing."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.MCR_IMPORT,
        start_date=None,
        end_date=datetime.now(timezone.utc),
    )

    transcription_waiting_time_settings = TranscriptionWaitingTimeSettings()

    default_meeting_processing_time = (
        int(transcription_waiting_time_settings.AVERAGE_MEETING_DURATION_HOURS * 60)
        // transcription_waiting_time_settings.AVERAGE_TRANSCRIPTION_SPEED
    )

    # Act
    start_time = datetime.now(timezone.utc)
    _ = mts.start_transcription(meeting_id=meeting.id)

    records = (
        db_session.query(MeetingTransitionRecord)
        .filter(MeetingTransitionRecord.meeting_id == meeting.id)
        .all()
    )

    # Verify a record was created with prediction
    assert len(records) == 1
    record = records[0]
    assert record.predicted_date_of_next_transition is not None

    # Verify the prediction is approximately the default time from now
    # Ensure timezone-aware comparison
    if record.predicted_date_of_next_transition.tzinfo is None:
        actual_prediction_time = record.predicted_date_of_next_transition.replace(
            tzinfo=timezone.utc, microsecond=0
        )
    else:
        actual_prediction_time = record.predicted_date_of_next_transition.replace(
            microsecond=0
        )

    expected_prediction_time = start_time.replace(microsecond=0) + timedelta(
        minutes=default_meeting_processing_time
    )

    # Allow 2 second tolerance for test execution time
    time_diff = abs((actual_prediction_time - expected_prediction_time).total_seconds())
    assert time_diff < 2


def test_fail_transcription() -> None:
    """Test transcription failure transitions to TRANSCRIPTION_FAILED."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )

    result = mts.fail_transcription(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_FAILED


def test_complete_transcription() -> None:
    """Test completing transcription transitions to TRANSCRIPTION_DONE."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    result = mts.complete_transcription(meeting_id=meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_DONE


# ---------------------------------------------------------------------------
# Tests – Report
# ---------------------------------------------------------------------------


def test_start_report(
    orchestrator_user: User,
    mock_celery_producer_app: Mock,
    user_keycloak_uuid: UUID,
) -> None:
    """Test starting report transitions to REPORT_PENDING."""
    meeting = MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
        transcription_filename="titre.docx",
    )

    result = mts.start_report(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.REPORT_PENDING


def test_complete_report(
    _mock_save_formatted_report: MagicMock, mock_send_email: MagicMock
) -> None:
    """Test completing report transitions to REPORT_DONE."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.REPORT_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )
    report_response = MagicMock()

    result = mts.complete_report(meeting_id=meeting.id, report_response=report_response)

    assert result.status == MeetingStatus.REPORT_DONE
    assert mock_send_email.call_count == 1


# ---------------------------------------------------------------------------
# Error case
# ---------------------------------------------------------------------------


def test_init_capture_bad_status(user_keycloak_uuid: UUID) -> None:
    """Test that init_capture raises exception when meeting is in wrong status."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(Exception):
        mts.init_capture(
            meeting_id=meeting.id,
            user_keycloak_uuid=user_keycloak_uuid,
        )
