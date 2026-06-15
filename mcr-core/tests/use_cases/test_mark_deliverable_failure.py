from sqlalchemy.orm import Session

from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.use_cases.mark_deliverable_failure import mark_deliverable_failure
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory


class TestMarkDeliverableFailure:
    def test_flips_deliverable_and_meeting_status(
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

        mark_deliverable_failure(deliverable_id=pending.id)

        db_session.refresh(pending)
        db_session.refresh(meeting)
        assert pending.status == DeliverableStatus.FAILED
        assert meeting.status == MeetingStatus.REPORT_FAILED
