from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import (
    BadRequestException,
    ForbiddenAccessException,
    NotFoundException,
)
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.orchestrators import deliverable_orchestrator as do
from mcr_meeting.app.schemas.report_generation import (
    ReportGenerationResponse,
    ReportHeader,
)
from tests.factories import MeetingFactory, UserFactory
from tests.factories.deliverable_factory import DeliverableFactory


def _decision_record_response() -> ReportGenerationResponse:
    return ReportGenerationResponse(
        header=ReportHeader(
            title="title",
            objective=None,
            participants=[],
            next_meeting=None,
        ),
        topics_with_decision=[],
        next_steps=[],
    )


@pytest.fixture
def mock_save_formatted_report(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    save_mock = MagicMock()
    monkeypatch.setattr(
        "mcr_meeting.app.statemachine_actions.meeting_actions.save_formatted_report",
        save_mock,
    )
    return save_mock


@pytest.fixture
def mock_generate_decision_docx(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    docx_mock = MagicMock()
    monkeypatch.setattr(
        "mcr_meeting.app.statemachine_actions.meeting_actions.generate_docx_decisions_reports_from_template",
        docx_mock,
    )
    return docx_mock


class TestRequestDeliverable:
    def test_creates_pending_row_and_dispatches_celery_with_deliverable_id(
        self,
        mock_celery_producer_app: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        deliverable = do.request_deliverable(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            type=DeliverableType.DECISION_RECORD,
        )

        assert deliverable.status == DeliverableStatus.PENDING
        assert deliverable.type == DeliverableType.DECISION_RECORD
        assert deliverable.meeting_id == meeting.id

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.REPORT_PENDING

        mock_celery_producer_app.send_task.assert_called_once()
        call = mock_celery_producer_app.send_task.call_args
        assert call.kwargs["args"][0] == meeting.id
        assert call.kwargs["args"][2] == "DECISION_RECORD"
        assert call.kwargs["kwargs"] == {
            "owner_keycloak_uuid": str(meeting.owner.keycloak_uuid),
            "deliverable_id": deliverable.id,
        }

    def test_rejects_transcription_type(
        self,
        mock_celery_producer_app: MagicMock,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        with pytest.raises(BadRequestException):
            do.request_deliverable(
                meeting_id=meeting.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
                type=DeliverableType.TRANSCRIPTION,
            )

        mock_celery_producer_app.send_task.assert_not_called()

    def test_rerequest_after_done_chains_reset_then_start(
        self,
        mock_celery_producer_app: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
            report_filename="report.docx",
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )

        new_deliverable = do.request_deliverable(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            type=DeliverableType.DETAILED_SYNTHESIS,
        )

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.REPORT_PENDING
        assert new_deliverable.status == DeliverableStatus.PENDING
        assert new_deliverable.type == DeliverableType.DETAILED_SYNTHESIS

        mock_celery_producer_app.send_task.assert_called_once()

    def test_rerequest_after_failed_chains_reset_then_start(
        self,
        mock_celery_producer_app: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_FAILED,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        new_deliverable = do.request_deliverable(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            type=DeliverableType.DECISION_RECORD,
        )

        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.REPORT_PENDING
        assert new_deliverable.status == DeliverableStatus.PENDING

    def test_concurrent_same_direction_does_not_5xx(
        self,
        mock_celery_producer_app: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )
        first = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        second = do.request_deliverable(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
            type=DeliverableType.DETAILED_SYNTHESIS,
        )

        assert second.id != first.id
        assert second.status == DeliverableStatus.PENDING
        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.REPORT_PENDING

    def test_403_for_non_owner(
        self,
        mock_celery_producer_app: MagicMock,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )
        intruder = UserFactory.create()

        with pytest.raises(ForbiddenAccessException):
            do.request_deliverable(
                meeting_id=meeting.id,
                user_keycloak_uuid=intruder.keycloak_uuid,
                type=DeliverableType.DECISION_RECORD,
            )


class TestMarkDeliverableSuccess:
    def test_flips_status_persists_url_and_completes_sm(
        self,
        mock_send_email: MagicMock,
        mock_save_formatted_report: MagicMock,
        mock_generate_decision_docx: MagicMock,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        pending = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        do.mark_deliverable_success(
            deliverable_id=pending.id,
            external_url="https://drive.example.com/abc",
            report_response=_decision_record_response(),
        )

        db_session.refresh(pending)
        db_session.refresh(meeting)
        assert pending.status == DeliverableStatus.AVAILABLE
        assert pending.external_url == "https://drive.example.com/abc"
        assert meeting.status == MeetingStatus.REPORT_DONE
        mock_send_email.assert_called_once()


class TestMarkDeliverableFailure:
    def test_flips_status_and_fails_sm(
        self,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        pending = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        do.mark_deliverable_failure(deliverable_id=pending.id)

        db_session.refresh(pending)
        db_session.refresh(meeting)
        assert pending.status == DeliverableStatus.FAILED
        assert meeting.status == MeetingStatus.REPORT_FAILED


class TestSoftDeleteDeliverable:
    def test_sets_status_deleted_and_resets_sm(
        self,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            report_filename="report.docx",
        )
        available = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )

        do.soft_delete_deliverable(
            deliverable_id=available.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
        )

        db_session.refresh(available)
        db_session.refresh(meeting)
        assert available.status == DeliverableStatus.DELETED
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE

    def test_403_for_non_owner(self) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            report_filename="report.docx",
        )
        available = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )
        intruder = UserFactory.create()

        with pytest.raises(ForbiddenAccessException):
            do.soft_delete_deliverable(
                deliverable_id=available.id,
                user_keycloak_uuid=intruder.keycloak_uuid,
            )


class TestListDeliverables:
    def test_returns_only_non_deleted_rows(
        self,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
        )
        kept_a = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )
        kept_b = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DETAILED_SYNTHESIS,
            status=DeliverableStatus.DELETED,
        )

        rows = do.list_deliverables_for_meeting(
            meeting_id=meeting.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
        )

        ids = {row.id for row in rows}
        assert ids == {kept_a.id, kept_b.id}

    def test_403_for_non_owner(self) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
        )
        intruder = UserFactory.create()

        with pytest.raises(ForbiddenAccessException):
            do.list_deliverables_for_meeting(
                meeting_id=meeting.id,
                user_keycloak_uuid=intruder.keycloak_uuid,
            )

    def test_404_for_unknown_meeting(self) -> None:
        user = UserFactory.create()

        with pytest.raises(NotFoundException):
            do.list_deliverables_for_meeting(
                meeting_id=999_999,
                user_keycloak_uuid=user.keycloak_uuid,
            )


class TestGetDeliverableFile:
    def test_streams_docx_from_s3(
        self,
        mocker: Any,
    ) -> None:
        from io import BytesIO

        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            report_filename="report.docx",
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )
        buffer = BytesIO(b"fake docx content")
        mocker.patch(
            "mcr_meeting.app.orchestrators.deliverable_orchestrator.get_formatted_report_from_s3",
            return_value=buffer,
        )

        result = do.get_deliverable_file(
            deliverable_id=deliverable.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
        )

        assert result.buffer is buffer
        assert result.meeting_name == meeting.name

    def test_404_for_soft_deleted_deliverable(
        self,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            report_filename="report.docx",
        )
        deleted = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.DELETED,
        )

        with pytest.raises(NotFoundException):
            do.get_deliverable_file(
                deliverable_id=deleted.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
            )
