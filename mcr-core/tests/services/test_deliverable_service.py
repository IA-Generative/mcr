import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.services import deliverable_service
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory


class TestFindActiveDeliverable:
    def test_returns_active_row_when_present(
        self,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE, name_platform=MeetingPlatforms.COMU
        )
        active = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )

        result = deliverable_service.find_active_deliverable(
            meeting_id=meeting.id, deliverable_type=DeliverableType.DECISION_RECORD
        )

        assert result is not None
        assert result.id == active.id

    def test_returns_none_when_missing(
        self,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
        )

        result = deliverable_service.find_active_deliverable(
            meeting_id=meeting.id, deliverable_type=DeliverableType.DECISION_RECORD
        )

        assert result is None

    def test_ignores_soft_deleted_rows(
        self,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE, name_platform=MeetingPlatforms.COMU
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.DELETED,
        )

        result = deliverable_service.find_active_deliverable(
            meeting_id=meeting.id, deliverable_type=DeliverableType.DECISION_RECORD
        )

        assert result is None

    def test_distinguishes_by_type(
        self,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE, name_platform=MeetingPlatforms.COMU
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )

        decision = deliverable_service.find_active_deliverable(
            meeting_id=meeting.id, deliverable_type=DeliverableType.DECISION_RECORD
        )
        synthesis = deliverable_service.find_active_deliverable(
            meeting_id=meeting.id, deliverable_type=DeliverableType.DETAILED_SYNTHESIS
        )

        assert decision is not None
        assert synthesis is None


class TestUniqueActiveConstraint:
    def test_two_active_rows_same_meeting_and_type_violates_partial_index(
        self,
        db_session: Session,
    ) -> None:
        """The partial unique index `uq_deliverable_meeting_type_active`
        rejects two non-DELETED rows for the same (meeting_id, type)."""
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE, name_platform=MeetingPlatforms.COMU
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        with pytest.raises(IntegrityError):
            with UnitOfWork():
                deliverable_service.create_pending_deliverable(
                    meeting_id=meeting.id,
                    deliverable_type=DeliverableType.DECISION_RECORD,
                )

    def test_deleted_row_does_not_block_active_row(
        self,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.DELETED,
        )

        # Should not raise — the DELETED row is excluded from the partial index.
        deliverable = deliverable_service.create_pending_deliverable(
            meeting_id=meeting.id, deliverable_type=DeliverableType.DECISION_RECORD
        )

        assert deliverable.status == DeliverableStatus.PENDING

    def test_different_types_coexist(
        self,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        deliverable = deliverable_service.create_pending_deliverable(
            meeting_id=meeting.id, deliverable_type=DeliverableType.DETAILED_SYNTHESIS
        )

        assert deliverable.status == DeliverableStatus.PENDING
