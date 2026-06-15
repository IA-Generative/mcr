import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import (
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
from mcr_meeting.app.use_cases.list_deliverables_for_meeting import (
    list_deliverables_for_meeting,
)
from tests.factories import MeetingFactory, UserFactory
from tests.factories.deliverable_factory import DeliverableFactory


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

        rows = list_deliverables_for_meeting(
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
            list_deliverables_for_meeting(
                meeting_id=meeting.id,
                user_keycloak_uuid=intruder.keycloak_uuid,
            )

    def test_404_for_unknown_meeting(self) -> None:
        user = UserFactory.create()

        with pytest.raises(NotFoundException):
            list_deliverables_for_meeting(
                meeting_id=999_999,
                user_keycloak_uuid=user.keycloak_uuid,
            )
