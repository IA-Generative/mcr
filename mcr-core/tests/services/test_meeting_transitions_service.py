from datetime import datetime, timezone
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
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.orchestrators import meeting_transitions_orchestrator as mts
from mcr_meeting.app.services import s3_service as s3s
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)
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
def _mock_wait_time(monkeypatch: Any) -> MagicMock:
    waiting_time_mock = MagicMock()

    monkeypatch.setattr(
        TranscriptionQueueEstimationService,
        "estimate_current_wait_time_minutes",
        lambda *_: 59,
    )

    return waiting_time_mock


@pytest.fixture
def _mock_transcription_object_name(monkeypatch: Any) -> MagicMock:
    transcription_object_name_mock = MagicMock()

    monkeypatch.setattr(
        s3s,
        "get_transcription_object_name",
        lambda *_: "titre.docx",
    )

    return transcription_object_name_mock


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
def _mock_transition_record_creation(monkeypatch: Any) -> MagicMock:
    transition_record_mock = MagicMock()

    monkeypatch.setattr(
        meeting_actions,
        "create_transcription_transition_record_with_estimation",
        transition_record_mock,
    )

    return transition_record_mock


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


# ---------------------------------------------------------------------------
# Tests – Transcription
# ---------------------------------------------------------------------------


def test_init_transcription(
    mock_celery_producer_app: Mock,
    _mock_wait_time: MagicMock,
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


def test_start_transcription_creates_log_with_prediction(
    _mock_transition_record_creation: MagicMock,
) -> None:
    """Test that start_transcription creates exactly one transition log with prediction."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.MCR_IMPORT,
        with_dates=True,
    )

    result = mts.start_transcription(meeting_id=meeting.id)

    # Assert
    assert result.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS
    assert _mock_transition_record_creation.call_count == 1


def test_start_transcription_missing_start_date_uses_default_prediction(
    _mock_transition_record_creation: MagicMock,
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
    _ = mts.start_transcription(meeting_id=meeting.id)

    # Assert
    call_args = _mock_transition_record_creation.call_args
    assert "waiting_time_minutes" in call_args[1]
    assert call_args[1]["waiting_time_minutes"] == default_meeting_processing_time


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
    _mock_transcription_object_name: MagicMock,
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


def test_complete_report(_mock_save_formatted_report: MagicMock) -> None:
    """Test completing report transitions to REPORT_DONE."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.REPORT_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )
    report_response = MagicMock()

    result = mts.complete_report(meeting_id=meeting.id, report_response=report_response)

    assert result.status == MeetingStatus.REPORT_DONE


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
