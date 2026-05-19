import pytest
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import DeliverableStateConflictException
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
from tests.mocks.in_memory_email import InMemoryEmailClient
from tests.mocks.in_memory_s3 import InMemoryS3


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
        pending = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
            external_url=None,
        )

        result = mark_deliverable_success(
            deliverable_id=pending.id,
            external_url=None,
            report_response=_decision_record_response(),
        )

        db_session.refresh(pending)
        db_session.refresh(meeting)
        assert result.status == DeliverableStatus.AVAILABLE
        assert pending.status == DeliverableStatus.AVAILABLE
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


class TestB2Regression:
    def test_s3_failure_leaves_deliverable_pending(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        in_memory_s3.should_fail_put = True
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        pending = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        with pytest.raises(RuntimeError):
            mark_deliverable_success(
                deliverable_id=pending.id,
                external_url=None,
                report_response=_decision_record_response(),
            )

        db_session.refresh(pending)
        db_session.refresh(meeting)
        assert pending.status == DeliverableStatus.PENDING
        assert meeting.status == MeetingStatus.REPORT_PENDING
        assert in_memory_s3.objects == {}
        assert in_memory_email.sent == []

    def test_render_failure_leaves_deliverable_pending(
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
        pending = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        with pytest.raises(RuntimeError):
            mark_deliverable_success(
                deliverable_id=pending.id,
                external_url=None,
                report_response=_decision_record_response(),
            )

        db_session.refresh(pending)
        db_session.refresh(meeting)
        assert pending.status == DeliverableStatus.PENDING
        assert meeting.status == MeetingStatus.REPORT_PENDING
        assert in_memory_s3.objects == {}
        assert in_memory_email.sent == []

    def test_replay_after_s3_failure_converges(
        self,
        db_session: Session,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
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

        in_memory_s3.should_fail_put = True
        with pytest.raises(RuntimeError):
            mark_deliverable_success(
                deliverable_id=pending.id,
                external_url=None,
                report_response=_decision_record_response(),
            )

        in_memory_s3.should_fail_put = False
        result = mark_deliverable_success(
            deliverable_id=pending.id,
            external_url=None,
            report_response=_decision_record_response(),
        )

        assert result.status == DeliverableStatus.AVAILABLE
        assert len(in_memory_s3.objects) == 1


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
        pending = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        result = mark_deliverable_success(
            deliverable_id=pending.id,
            external_url=None,
            report_response=_decision_record_response(),
        )

        db_session.refresh(pending)
        db_session.refresh(meeting)
        assert result.status == DeliverableStatus.AVAILABLE
        assert pending.status == DeliverableStatus.AVAILABLE
        assert meeting.status == MeetingStatus.REPORT_DONE


class TestConflict:
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
                external_url=None,
                report_response=_decision_record_response(),
            )

        assert in_memory_email.sent == []
