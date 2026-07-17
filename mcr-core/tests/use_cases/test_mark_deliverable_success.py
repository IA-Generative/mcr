import pytest
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import DeliverableStateConflictException
from mcr_meeting.app.infrastructure.redis import get_refresh_token, save_refresh_token
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.report_generation import (
    ReportGenerationResponse,
    ReportHeader,
)
from mcr_meeting.app.use_cases.mark_deliverable_success import (
    mark_deliverable_success,
)
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory
from tests.mocks.in_memory_drive import InMemoryDriveClient
from tests.mocks.in_memory_email import InMemoryEmailClient
from tests.mocks.in_memory_keycloak import InMemoryKeycloak
from tests.mocks.in_memory_s3 import InMemoryS3, S3Op


def _decision_record_response() -> ReportGenerationResponse:
    return ReportGenerationResponse(
        header=ReportHeader(
            title="Title", objective=None, participants=[], next_meeting=None
        ),
        topics_with_decision=[],
        next_steps=[],
    )


class TestHappyPath:
    def test_flips_to_available_uploads_to_s3_and_notifies(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
            external_url=None,
        )

        result = mark_deliverable_success(
            deliverable_id=in_progress_deliverable.id,
            report_response=_decision_record_response(),
        )

        db_session.refresh(in_progress_deliverable)
        db_session.refresh(meeting)
        assert result.status == DeliverableStatus.AVAILABLE
        assert in_progress_deliverable.status == DeliverableStatus.AVAILABLE
        assert meeting.status == MeetingStatus.REPORT_DONE
        assert len(in_memory_s3.objects) == 1
        uploaded_key = next(iter(in_memory_s3.objects))
        assert uploaded_key.endswith("decision_record.docx")
        assert len(in_memory_email.sent) == 1
        records = (
            db_session.query(MeetingTransitionRecord)
            .filter(
                MeetingTransitionRecord.meeting_id == meeting.id,
                MeetingTransitionRecord.status == MeetingStatus.REPORT_DONE,
            )
            .all()
        )
        assert len(records) == 1


class TestDriveUpload:
    def test_persists_drive_url_when_upload_succeeds(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        in_memory_drive: InMemoryDriveClient,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        save_refresh_token(str(meeting.owner.keycloak_uuid), "refresh-token")
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        result = mark_deliverable_success(
            deliverable_id=in_progress_deliverable.id,
            report_response=_decision_record_response(),
        )

        db_session.refresh(in_progress_deliverable)
        assert result.status == DeliverableStatus.AVAILABLE
        assert in_progress_deliverable.external_url == in_memory_drive.url

    def test_drive_upload_failure_is_best_effort(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        in_memory_drive: InMemoryDriveClient,
    ) -> None:
        in_memory_drive.should_fail = True
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        save_refresh_token(str(meeting.owner.keycloak_uuid), "refresh-token")
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        result = mark_deliverable_success(
            deliverable_id=in_progress_deliverable.id,
            report_response=_decision_record_response(),
        )

        db_session.refresh(in_progress_deliverable)
        db_session.refresh(meeting)
        assert result.status == DeliverableStatus.AVAILABLE
        assert in_progress_deliverable.external_url is None
        assert meeting.status == MeetingStatus.REPORT_DONE
        assert len(in_memory_email.sent) == 1

    def test_skips_drive_when_no_refresh_token(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        in_memory_drive: InMemoryDriveClient,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        result = mark_deliverable_success(
            deliverable_id=in_progress_deliverable.id,
            report_response=_decision_record_response(),
        )

        db_session.refresh(in_progress_deliverable)
        assert result.status == DeliverableStatus.AVAILABLE
        assert in_progress_deliverable.external_url is None

    def test_drops_refresh_token_when_refresh_fails(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        in_memory_keycloak: InMemoryKeycloak,
    ) -> None:
        in_memory_keycloak.should_fail_refresh = True
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        user_sub = str(meeting.owner.keycloak_uuid)
        save_refresh_token(user_sub, "refresh-token")
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        result = mark_deliverable_success(
            deliverable_id=in_progress_deliverable.id,
            report_response=_decision_record_response(),
        )

        db_session.refresh(in_progress_deliverable)
        assert result.status == DeliverableStatus.AVAILABLE
        assert in_progress_deliverable.external_url is None
        assert get_refresh_token(user_sub) is None

    def test_persists_rotated_refresh_token(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        in_memory_keycloak: InMemoryKeycloak,
        in_memory_drive: InMemoryDriveClient,
    ) -> None:
        in_memory_keycloak.rotated_refresh_token = "rotated-token"
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        user_sub = str(meeting.owner.keycloak_uuid)
        save_refresh_token(user_sub, "refresh-token")
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        mark_deliverable_success(
            deliverable_id=in_progress_deliverable.id,
            report_response=_decision_record_response(),
        )

        assert get_refresh_token(user_sub) == "rotated-token"


class TestFailureRollback:
    def test_s3_failure_marks_deliverable_failed(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        in_memory_s3.fail(S3Op.PUT, RuntimeError("S3 put failed"))
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        with pytest.raises(RuntimeError):
            mark_deliverable_success(
                deliverable_id=in_progress_deliverable.id,
                report_response=_decision_record_response(),
            )

        db_session.refresh(in_progress_deliverable)
        db_session.refresh(meeting)
        assert in_progress_deliverable.status == DeliverableStatus.FAILED
        assert meeting.status == MeetingStatus.REPORT_PENDING
        assert in_memory_s3.objects == {}
        assert in_memory_email.sent == []

    def test_render_failure_marks_deliverable_failed(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "mcr_meeting.app.use_cases.mark_deliverable_success.render_report",
            side_effect=RuntimeError("render boom"),
        )
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        with pytest.raises(RuntimeError):
            mark_deliverable_success(
                deliverable_id=in_progress_deliverable.id,
                report_response=_decision_record_response(),
            )

        db_session.refresh(in_progress_deliverable)
        db_session.refresh(meeting)
        assert in_progress_deliverable.status == DeliverableStatus.FAILED
        assert meeting.status == MeetingStatus.REPORT_PENDING
        assert in_memory_s3.objects == {}
        assert in_memory_email.sent == []

    def test_replay_after_failure_raises_conflict(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        in_memory_s3.fail(S3Op.PUT, RuntimeError("S3 put failed"), times=1)
        with pytest.raises(RuntimeError):
            mark_deliverable_success(
                deliverable_id=in_progress_deliverable.id,
                report_response=_decision_record_response(),
            )

        with pytest.raises(DeliverableStateConflictException):
            mark_deliverable_success(
                deliverable_id=in_progress_deliverable.id,
                report_response=_decision_record_response(),
            )


class TestPostCommitFailures:
    def test_notification_failure_is_non_fatal(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        in_memory_email.should_fail = True
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        result = mark_deliverable_success(
            deliverable_id=in_progress_deliverable.id,
            report_response=_decision_record_response(),
        )

        db_session.refresh(in_progress_deliverable)
        db_session.refresh(meeting)
        assert result.status == DeliverableStatus.AVAILABLE
        assert in_progress_deliverable.status == DeliverableStatus.AVAILABLE
        assert meeting.status == MeetingStatus.REPORT_DONE


class TestConflict:
    def test_raises_when_still_pending(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        pending_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        with pytest.raises(DeliverableStateConflictException):
            mark_deliverable_success(
                deliverable_id=pending_deliverable.id,
                report_response=_decision_record_response(),
            )

        db_session.refresh(pending_deliverable)
        assert pending_deliverable.status == DeliverableStatus.PENDING
        assert in_memory_email.sent == []

    def test_raises_when_already_available(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
        )
        existing = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )

        with pytest.raises(DeliverableStateConflictException):
            mark_deliverable_success(
                deliverable_id=existing.id,
                report_response=_decision_record_response(),
            )

        assert in_memory_email.sent == []
