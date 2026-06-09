from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from mcr_meeting.app.db.deliverable_repository import (
    find_active_by_meeting_and_type,
)
from mcr_meeting.app.exceptions.exceptions import (
    DeliverableConcurrentlyCreatedException,
    ForbiddenAccessException,
    MeetingStateConflictException,
    TaskCreationException,
)
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.use_cases.request_deliverable import (
    request_deliverable as request_deliverable_use_case,
)
from tests.factories import MeetingFactory, UserFactory
from tests.factories.deliverable_factory import DeliverableFactory


@pytest.fixture
def mock_use_case_celery(mocker: MockerFixture) -> MagicMock:
    """The use case imports celery_producer_app directly, so the patch path
    must target the use case module — not the SM actions module that the
    global fixture patches."""
    return mocker.patch(
        "mcr_meeting.app.use_cases.request_deliverable.celery_producer_app"
    )


class TestRequestDeliverableHappyPath:
    def test_creates_pending_row_and_dispatches_celery_with_deliverable_id(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        assert deliverable.status == DeliverableStatus.PENDING
        assert deliverable.type == DeliverableType.DECISION_RECORD
        assert deliverable.meeting_id == meeting.id

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.REPORT_PENDING

        mock_use_case_celery.send_task.assert_called_once()
        call = mock_use_case_celery.send_task.call_args
        assert call.kwargs["args"][0] == meeting.id
        assert call.kwargs["args"][2] == "DECISION_RECORD"
        assert call.kwargs["kwargs"] == {
            "owner_keycloak_uuid": str(meeting.owner.keycloak_uuid),
            "deliverable_id": deliverable.id,
        }

    def test_passes_custom_prompt_through(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.CUSTOM_REPORT,
            custom_prompt="Analyse les risques",
        )

        call = mock_use_case_celery.send_task.call_args
        assert call.kwargs["args"][2] == "CUSTOM_REPORT"
        assert call.kwargs["kwargs"]["custom_prompt"] == "Analyse les risques"
        assert call.kwargs["kwargs"]["deliverable_id"] == deliverable.id

    def test_no_custom_prompt_key_for_standard_types(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        call = mock_use_case_celery.send_task.call_args
        assert "custom_prompt" not in call.kwargs["kwargs"]

    def test_passes_meeting_notes_through(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
            notes="Points discutés : roadmap Q3 et budget",
        )

        request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        call = mock_use_case_celery.send_task.call_args
        assert (
            call.kwargs["kwargs"]["notes_content"]
            == "Points discutés : roadmap Q3 et budget"
        )

    def test_no_notes_content_key_when_meeting_has_no_notes(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
            notes=None,
        )

        request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        call = mock_use_case_celery.send_task.call_args
        assert "notes_content" not in call.kwargs["kwargs"]


class TestRequestDeliverableExistingActive:
    def test_pending_same_type_returns_existing_no_new_task(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )
        existing = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        result = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        assert result.id == existing.id
        mock_use_case_celery.send_task.assert_not_called()

    def test_available_same_type_soft_deletes_and_creates_new(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
            report_filename="decision.docx",
        )
        previous = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )

        new_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        db_session.refresh(previous)
        db_session.refresh(meeting)
        assert previous.status == DeliverableStatus.DELETED
        assert new_deliverable.id != previous.id
        assert new_deliverable.status == DeliverableStatus.PENDING
        assert meeting.status == MeetingStatus.REPORT_PENDING
        mock_use_case_celery.send_task.assert_called_once()

    def test_failed_same_type_soft_deletes_and_creates_new(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_FAILED,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )
        previous = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.FAILED,
        )

        new_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        db_session.refresh(previous)
        db_session.refresh(meeting)
        assert previous.status == DeliverableStatus.DELETED
        assert new_deliverable.status == DeliverableStatus.PENDING
        assert meeting.status == MeetingStatus.REPORT_PENDING


class TestRequestDeliverableMeetingInTerminalReportState:
    def test_report_done_validates_reset_then_starts(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
            report_filename="report.docx",
        )

        deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DETAILED_SYNTHESIS,
        )

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.REPORT_PENDING
        assert deliverable.type == DeliverableType.DETAILED_SYNTHESIS
        mock_use_case_celery.send_task.assert_called_once()

    def test_report_failed_validates_reset_then_starts(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_FAILED,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.REPORT_PENDING


class TestRequestDeliverableIllegalTransition:
    def test_capture_in_progress_blocks_start_report(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.CAPTURE_IN_PROGRESS,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        with pytest.raises(MeetingStateConflictException):
            request_deliverable_use_case(
                meeting_id=meeting.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
                deliverable_type=DeliverableType.DECISION_RECORD,
            )

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.CAPTURE_IN_PROGRESS
        mock_use_case_celery.send_task.assert_not_called()


class TestRequestDeliverableAuth:
    def test_403_for_non_owner(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )
        intruder = UserFactory.create()

        with pytest.raises(ForbiddenAccessException):
            request_deliverable_use_case(
                meeting_id=meeting.id,
                user_keycloak_uuid=intruder.keycloak_uuid,
                deliverable_type=DeliverableType.DECISION_RECORD,
            )
        mock_use_case_celery.send_task.assert_not_called()


class TestRequestDeliverableConcurrentInsertRecovery:
    def test_concurrent_insert_returns_winning_row(
        self,
        mock_use_case_celery: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """If two requests race and the second INSERT trips the partial
        unique index, the use case must reload and return the winning row."""
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )
        winner = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        find_mock = mocker.patch(
            "mcr_meeting.app.use_cases.request_deliverable.find_active_by_meeting_and_type",
            side_effect=[None, winner],
        )
        mocker.patch(
            "mcr_meeting.app.use_cases.request_deliverable.save_deliverable",
            side_effect=DeliverableConcurrentlyCreatedException("race"),
        )

        result = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        assert result.id == winner.id
        assert find_mock.call_count == 2


class TestRequestDeliverableCeleryDispatchFailure:
    def test_dispatch_failure_rolls_back_deliverable_and_meeting_status(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        """Celery dispatch happens inside the UnitOfWork — when it raises, the
        savepoint reverts the PENDING deliverable INSERT and the meeting
        status update, so the request leaves no orphan rows."""
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )
        mock_use_case_celery.send_task.side_effect = RuntimeError("broker down")

        with pytest.raises(TaskCreationException):
            request_deliverable_use_case(
                meeting_id=meeting.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
                deliverable_type=DeliverableType.DECISION_RECORD,
            )

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE

        existing = find_active_by_meeting_and_type(
            meeting_id=meeting.id, deliverable_type=DeliverableType.DECISION_RECORD
        )
        assert existing is None

    def test_retry_after_dispatch_failure_creates_fresh_cycle(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )
        mock_use_case_celery.send_task.side_effect = RuntimeError("broker down")

        with pytest.raises(TaskCreationException):
            request_deliverable_use_case(
                meeting_id=meeting.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
                deliverable_type=DeliverableType.DECISION_RECORD,
            )

        mock_use_case_celery.send_task.side_effect = None
        mock_use_case_celery.send_task.reset_mock()

        new_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.REPORT_PENDING
        assert new_deliverable.status == DeliverableStatus.PENDING
        mock_use_case_celery.send_task.assert_called_once()
