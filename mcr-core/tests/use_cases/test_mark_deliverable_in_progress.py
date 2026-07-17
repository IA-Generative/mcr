import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import (
    DeliverableStateConflictException,
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
from mcr_meeting.app.use_cases.mark_deliverable_in_progress import (
    mark_deliverable_in_progress,
)
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory


class TestMarkDeliverableInProgress:
    def test_flips_pending_to_in_progress_without_touching_meeting(
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

        result = mark_deliverable_in_progress(deliverable_id=pending.id)

        db_session.refresh(pending)
        db_session.refresh(meeting)
        assert result.status == DeliverableStatus.IN_PROGRESS
        assert pending.status == DeliverableStatus.IN_PROGRESS
        assert meeting.status == MeetingStatus.REPORT_PENDING

    def test_raises_conflict_when_already_in_progress(
        self,
        db_session: Session,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        with pytest.raises(DeliverableStateConflictException):
            mark_deliverable_in_progress(deliverable_id=deliverable.id)

    def test_raises_not_found_for_unknown_deliverable(
        self,
        db_session: Session,
    ) -> None:
        with pytest.raises(NotFoundException):
            mark_deliverable_in_progress(deliverable_id=999999)
