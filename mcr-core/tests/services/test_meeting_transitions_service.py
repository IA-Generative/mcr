# type: ignore[explicit-any]

from typing import Any, Dict
from unittest.mock import MagicMock, Mock
from uuid import UUID

import pytest

from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.orchestrators import meeting_transitions_orchestrator as mts
from mcr_meeting.app.services import s3_service as s3s
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)
from mcr_meeting.app.statemachine_actions import meeting_actions

# ---------------------------------------------------------------------------
# Dummy model
# ---------------------------------------------------------------------------


class DummyMeeting:
    def __init__(
        self,
        status: MeetingStatus,
        name_platform: MeetingPlatforms,
        id: int,
    ) -> None:
        self.status = status
        self.name_platform = name_platform
        self.id = id
        self.name = "Dummy Meeting"
        self.transcription_filename = "titre.docx"

        self.owner = MagicMock()
        self.owner.keycloak_uuid = UUID("00000000-0000-0000-0000-000000000001")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_keycloak_uuid() -> UUID:
    return UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def visio_meeting() -> DummyMeeting:
    return DummyMeeting(
        status=MeetingStatus.NONE,
        name_platform=MeetingPlatforms.COMU,
        id=1,
    )


@pytest.fixture
def import_meeting() -> DummyMeeting:
    return DummyMeeting(
        status=MeetingStatus.IMPORT_PENDING,
        name_platform=MeetingPlatforms.MCR_IMPORT,
        id=2,
    )


@pytest.fixture
def record_meeting() -> DummyMeeting:
    return DummyMeeting(
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.MCR_RECORD,
        id=3,
    )


@pytest.fixture
def meeting_store(
    visio_meeting: DummyMeeting,
    import_meeting: DummyMeeting,
    record_meeting: DummyMeeting,
    user_keycloak_uuid: UUID,
) -> Dict[int, DummyMeeting]:
    for meeting in (visio_meeting, import_meeting, record_meeting):
        meeting.owner = MagicMock()
        meeting.owner.keycloak_uuid = user_keycloak_uuid

    return {
        visio_meeting.id: visio_meeting,
        import_meeting.id: import_meeting,
        record_meeting.id: record_meeting,
    }


@pytest.fixture
def _mock_db(monkeypatch: Any, meeting_store: Dict[int, DummyMeeting]) -> MagicMock:
    db_mock = MagicMock()

    def mock_update_meeting_status(
        meeting: DummyMeeting,
        meeting_status: MeetingStatus,
    ) -> DummyMeeting:
        meeting.status = meeting_status
        return meeting

    monkeypatch.setattr(
        meeting_actions,
        "update_meeting_status",
        mock_update_meeting_status,
    )

    def mock_get_meeting_service(*, meeting_id: int, **_: Any) -> DummyMeeting:
        return meeting_store[meeting_id]

    monkeypatch.setattr(
        mts,
        "get_meeting_service",
        mock_get_meeting_service,
    )

    return db_mock


@pytest.fixture
def _mock_waiting_time(monkeypatch: Any) -> MagicMock:
    waiting_time_mock = MagicMock()

    monkeypatch.setattr(
        TranscriptionQueueEstimationService,
        "get_meeting_transcription_waiting_time_minutes",
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


# ---------------------------------------------------------------------------
# Tests – Capture
# ---------------------------------------------------------------------------


def test_init_capture(
    _mock_db: MagicMock,
    visio_meeting: DummyMeeting,
    user_keycloak_uuid: UUID,
) -> None:
    visio_meeting.status = MeetingStatus.NONE

    result = mts.init_capture(
        meeting_id=visio_meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_PENDING


def test_start_capture(
    _mock_db: MagicMock,
    visio_meeting: DummyMeeting,
    user_keycloak_uuid: UUID,
) -> None:
    visio_meeting.status = MeetingStatus.CAPTURE_PENDING

    result = mts.start_capture(
        meeting_id=visio_meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_BOT_IS_CONNECTING


def test_complete_capture(
    _mock_db: MagicMock,
    visio_meeting: DummyMeeting,
    user_keycloak_uuid: UUID,
) -> None:
    visio_meeting.status = MeetingStatus.CAPTURE_IN_PROGRESS

    result = mts.complete_capture(
        meeting_id=visio_meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )
    assert result.status == MeetingStatus.CAPTURE_DONE


def test_start_capture_bot(
    _mock_db: MagicMock,
    visio_meeting: DummyMeeting,
    user_keycloak_uuid: UUID,
) -> None:
    visio_meeting.status = MeetingStatus.CAPTURE_BOT_IS_CONNECTING

    result = mts.start_capture_bot(
        meeting_id=visio_meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_IN_PROGRESS


def test_fail_capture_bot(
    _mock_db: MagicMock,
    visio_meeting: DummyMeeting,
    user_keycloak_uuid: UUID,
) -> None:
    visio_meeting.status = MeetingStatus.CAPTURE_BOT_IS_CONNECTING

    result = mts.fail_capture_bot(
        meeting_id=visio_meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_BOT_CONNECTION_FAILED


def test_fail_capture(
    _mock_db: MagicMock,
    visio_meeting: DummyMeeting,
    user_keycloak_uuid: UUID,
) -> None:
    visio_meeting.status = MeetingStatus.CAPTURE_IN_PROGRESS

    result = mts.fail_capture(
        meeting_id=visio_meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_FAILED


# ---------------------------------------------------------------------------
# Tests – Transcription
# ---------------------------------------------------------------------------


def test_init_transcription(
    _mock_db: MagicMock,
    mock_celery_producer_app: Mock,
    _mock_waiting_time: MagicMock,
    import_meeting: DummyMeeting,
    user_keycloak_uuid: UUID,
) -> None:
    import_meeting.status = MeetingStatus.IMPORT_PENDING

    result = mts.init_transcription(
        meeting_id=import_meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.TRANSCRIPTION_PENDING


def test_start_transcription(_mock_db: MagicMock, import_meeting: DummyMeeting) -> None:
    import_meeting.status = MeetingStatus.TRANSCRIPTION_PENDING

    result = mts.start_transcription(meeting_id=import_meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS


def test_fail_transcription(_mock_db: MagicMock, visio_meeting: DummyMeeting) -> None:
    visio_meeting.status = MeetingStatus.TRANSCRIPTION_PENDING

    result = mts.fail_transcription(meeting_id=visio_meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_FAILED


def test_complete_transcription(
    _mock_db: MagicMock, visio_meeting: DummyMeeting
) -> None:
    visio_meeting.status = MeetingStatus.TRANSCRIPTION_IN_PROGRESS

    result = mts.complete_transcription(meeting_id=visio_meeting.id)

    assert result.status == MeetingStatus.TRANSCRIPTION_DONE


# ---------------------------------------------------------------------------
# Tests – Report
# ---------------------------------------------------------------------------


def test_start_report(
    _mock_db: MagicMock,
    _mock_transcription_object_name: MagicMock,
    mock_celery_producer_app: Mock,
    visio_meeting: DummyMeeting,
    user_keycloak_uuid: UUID,
) -> None:
    visio_meeting.status = MeetingStatus.TRANSCRIPTION_DONE

    result = mts.start_report(
        meeting_id=visio_meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.REPORT_PENDING


def test_complete_report(
    _mock_db: MagicMock,
    _mock_save_formatted_report: MagicMock,
    visio_meeting: DummyMeeting,
) -> None:
    visio_meeting.status = MeetingStatus.REPORT_PENDING
    report_response = MagicMock()

    result = mts.complete_report(
        meeting_id=visio_meeting.id, report_response=report_response
    )

    assert result.status == MeetingStatus.REPORT_DONE


# ---------------------------------------------------------------------------
# Error case
# ---------------------------------------------------------------------------


def test_init_capture_bad_status(
    visio_meeting: DummyMeeting,
    user_keycloak_uuid: UUID,
    _mock_db: MagicMock,
) -> None:
    visio_meeting.status = MeetingStatus.REPORT_DONE

    with pytest.raises(Exception):
        mts.init_capture(
            meeting_id=visio_meeting.id,
            user_keycloak_uuid=user_keycloak_uuid,
        )
