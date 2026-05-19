from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
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

        with pytest.raises(ValueError):
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


class TestRequestDeliverableIntegrityErrorRecovery:
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

        # Simulate the race: find_active_by_meeting_and_type returned None at
        # first (the winner row was not yet visible), then save_deliverable
        # raised IntegrityError, then a fresh lookup finds the winner.
        find_mock = mocker.patch(
            "mcr_meeting.app.use_cases.request_deliverable.find_active_by_meeting_and_type",
            side_effect=[None, winner],
        )
        mocker.patch(
            "mcr_meeting.app.use_cases.request_deliverable.save_deliverable",
            side_effect=IntegrityError("INSERT", {}, Exception()),
        )

        result = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        assert result.id == winner.id
        assert find_mock.call_count == 2


class TestRequestDeliverableCeleryFailureCompensation:
    def test_dispatch_failure_marks_deliverable_failed_and_meeting_report_failed(
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

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.REPORT_FAILED

        # The deliverable created during the failed cycle must be marked FAILED
        # so that a subsequent request_deliverable_use_case soft-deletes it and
        # restarts a fresh cycle.
        from mcr_meeting.app.db.deliverable_repository import (
            find_active_by_meeting_and_type,
        )

        existing = find_active_by_meeting_and_type(
            meeting_id=meeting.id, deliverable_type=DeliverableType.DECISION_RECORD
        )
        assert existing is not None
        assert existing.status == DeliverableStatus.FAILED

    def test_retry_after_dispatch_failure_creates_fresh_cycle(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        """The compensation must leave the system in a state where the user's
        next click produces a fresh deliverable and a Celery task."""
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

        # Second attempt: Celery is back, retry succeeds
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

    def test_compensation_failure_is_logged_but_original_exception_raised(
        self,
        mock_use_case_celery: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )
        mock_use_case_celery.send_task.side_effect = RuntimeError("broker down")
        mocker.patch(
            "mcr_meeting.app.use_cases.request_deliverable.set_deliverable_status",
            side_effect=RuntimeError("db down too"),
        )

        with pytest.raises(TaskCreationException) as exc_info:
            request_deliverable_use_case(
                meeting_id=meeting.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
                deliverable_type=DeliverableType.DECISION_RECORD,
            )

        assert "broker down" in str(exc_info.value)
