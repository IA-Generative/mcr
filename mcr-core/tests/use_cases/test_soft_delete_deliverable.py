import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.use_cases.soft_delete_deliverable import soft_delete_deliverable
from tests.factories import MeetingFactory, UserFactory
from tests.factories.deliverable_factory import DeliverableFactory


class TestSoftDeleteDeliverable:
    def test_sets_status_deleted(
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

        soft_delete_deliverable(
            deliverable_id=available.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
        )

        db_session.refresh(available)
        assert available.status == DeliverableStatus.DELETED

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
            soft_delete_deliverable(
                deliverable_id=available.id,
                user_keycloak_uuid=intruder.keycloak_uuid,
            )
