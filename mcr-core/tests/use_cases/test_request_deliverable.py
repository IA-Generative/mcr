from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from mcr_meeting.app.db.deliverable_repository import (
    get_active_by_meeting_and_type,
)
from mcr_meeting.app.exceptions.exceptions import (
    DeliverableConcurrentlyCreatedException,
    ForbiddenAccessException,
    NotFoundException,
    TaskCreationException,
)
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    Meeting,
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
    """Report dispatch goes through the infra celery wrapper, so patch the
    broker there — the use case no longer references celery_producer_app."""
    return mocker.patch("mcr_meeting.app.infrastructure.celery.celery_producer_app")


def _transcribed_meeting(**kwargs: object) -> Meeting:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
        transcription_filename="transcription.docx",
        **kwargs,
    )
    DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=DeliverableStatus.AVAILABLE,
    )
    return meeting


def _transcribing_meeting() -> Meeting:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )
    DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=DeliverableStatus.IN_PROGRESS,
    )
    return meeting


class TestRequestDeliverableHappyPath:
    def test_creates_pending_row_and_dispatches_celery_with_deliverable_id(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = _transcribed_meeting()

        deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        assert deliverable.status == DeliverableStatus.PENDING
        assert deliverable.type == DeliverableType.DECISION_RECORD
        assert deliverable.meeting_id == meeting.id

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE

        mock_use_case_celery.send_task.assert_called_once()
        call = mock_use_case_celery.send_task.call_args
        assert call.kwargs["args"][0] == meeting.id
        assert call.kwargs["args"][2] == "DECISION_RECORD"
        assert call.kwargs["kwargs"] == {
            "owner_keycloak_uuid": str(meeting.owner.keycloak_uuid),
            "deliverable_id": deliverable.id,
        }
        assert call.kwargs["countdown"] >= 0

    def test_structured_minutes_dispatches_generation_with_matching_report_type(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = _transcribed_meeting()

        deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.STRUCTURED_MINUTES,
        )

        assert deliverable.status == DeliverableStatus.PENDING
        assert deliverable.type == DeliverableType.STRUCTURED_MINUTES
        call = mock_use_case_celery.send_task.call_args
        assert call.kwargs["args"][2] == "STRUCTURED_MINUTES"

    def test_passes_custom_prompt_through(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = _transcribed_meeting()

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
        meeting = _transcribed_meeting()

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
        meeting = _transcribed_meeting(
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
        meeting = _transcribed_meeting(notes=None)

        request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        call = mock_use_case_celery.send_task.call_args
        assert "notes_content" not in call.kwargs["kwargs"]


class TestRequestDeliverableDuringTranscription:
    def test_queues_requested_without_dispatch_while_transcription_runs(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = _transcribing_meeting()

        deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        assert deliverable.status == DeliverableStatus.REQUESTED
        assert deliverable.type == DeliverableType.DECISION_RECORD
        mock_use_case_celery.send_task.assert_not_called()

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS

    def test_persists_custom_prompt_on_the_requested_row(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = _transcribing_meeting()

        deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.CUSTOM_REPORT,
            custom_prompt="Analyse les risques",
        )

        assert deliverable.status == DeliverableStatus.REQUESTED
        assert deliverable.custom_prompt == "Analyse les risques"
        mock_use_case_celery.send_task.assert_not_called()

    def test_second_request_same_type_deduplicates_the_queue(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = _transcribing_meeting()

        first_requested_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )
        second_requested_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        assert first_requested_deliverable.id == second_requested_deliverable.id
        assert second_requested_deliverable.status == DeliverableStatus.REQUESTED
        mock_use_case_celery.send_task.assert_not_called()


class TestRequestDeliverableExistingActive:
    def test_pending_same_type_returns_existing_no_new_task(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = _transcribed_meeting()
        existing_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        resulted_requested_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        assert resulted_requested_deliverable.id == existing_deliverable.id
        mock_use_case_celery.send_task.assert_not_called()

    def test_available_same_type_soft_deletes_and_creates_new(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = _transcribed_meeting(report_filename="decision.docx")
        previously_requested_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )

        newly_requested_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        db_session.refresh(previously_requested_deliverable)
        db_session.refresh(meeting)
        assert previously_requested_deliverable.status == DeliverableStatus.DELETED
        assert newly_requested_deliverable.id != previously_requested_deliverable.id
        assert newly_requested_deliverable.status == DeliverableStatus.PENDING
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE
        mock_use_case_celery.send_task.assert_called_once()

    def test_failed_same_type_soft_deletes_and_creates_new(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = _transcribed_meeting()
        previously_requested_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.FAILED,
        )

        newly_requested_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        db_session.refresh(previously_requested_deliverable)
        db_session.refresh(meeting)
        assert previously_requested_deliverable.status == DeliverableStatus.DELETED
        assert newly_requested_deliverable.status == DeliverableStatus.PENDING
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE

    def test_failed_same_type_requeues_when_transcription_still_running(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = _transcribing_meeting()
        previously_requested_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.FAILED,
        )

        newly_requested_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )

        db_session.refresh(previously_requested_deliverable)
        assert previously_requested_deliverable.status == DeliverableStatus.DELETED
        assert newly_requested_deliverable.status == DeliverableStatus.REQUESTED
        mock_use_case_celery.send_task.assert_not_called()


class TestRequestDeliverableMultipleTypes:
    def test_second_report_type_does_not_conflict(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = _transcribed_meeting()

        first_requested_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DECISION_RECORD,
        )
        second_requested_deliverable = request_deliverable_use_case(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            deliverable_type=DeliverableType.DETAILED_SYNTHESIS,
        )

        db_session.refresh(meeting)
        assert first_requested_deliverable.status == DeliverableStatus.PENDING
        assert second_requested_deliverable.status == DeliverableStatus.PENDING
        assert first_requested_deliverable.id != second_requested_deliverable.id
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE
        assert mock_use_case_celery.send_task.call_count == 2


class TestRequestDeliverableAuth:
    def test_403_for_non_owner(
        self,
        mock_use_case_celery: MagicMock,
    ) -> None:
        meeting = _transcribed_meeting()
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
        meeting = _transcribed_meeting()
        winner = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        get_mock = mocker.patch(
            "mcr_meeting.app.use_cases.request_deliverable.get_active_by_meeting_and_type",
            side_effect=[NotFoundException("none yet"), winner],
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
        assert get_mock.call_count == 2


class TestRequestDeliverableCeleryDispatchFailure:
    def test_dispatch_failure_rolls_back_deliverable_and_meeting_status(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        """Celery dispatch happens inside the UnitOfWork — when it raises, the
        savepoint reverts the PENDING deliverable INSERT and the meeting
        status update, so the request leaves no orphan rows."""
        meeting = _transcribed_meeting()
        mock_use_case_celery.send_task.side_effect = RuntimeError("broker down")

        with pytest.raises(TaskCreationException):
            request_deliverable_use_case(
                meeting_id=meeting.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
                deliverable_type=DeliverableType.DECISION_RECORD,
            )

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE

        with pytest.raises(NotFoundException):
            get_active_by_meeting_and_type(
                meeting_id=meeting.id, deliverable_type=DeliverableType.DECISION_RECORD
            )

    def test_retry_after_dispatch_failure_creates_fresh_cycle(
        self,
        mock_use_case_celery: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = _transcribed_meeting()
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
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE
        assert new_deliverable.status == DeliverableStatus.PENDING
        mock_use_case_celery.send_task.assert_called_once()
