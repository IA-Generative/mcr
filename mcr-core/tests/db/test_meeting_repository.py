from mcr_meeting.app.db.meeting_repository import get_meetings_by_user_id
from tests.factories import MeetingFactory, UserFactory
from mcr_meeting.app.models import MeetingStatus


def test_get_meetings_by_user_id_filters_deleted():

    user = UserFactory.create(first_name="John", last_name="Doe")

    active1 = MeetingFactory.create(owner=user, status=MeetingStatus.IMPORT_PENDING)
    active2 = MeetingFactory.create(owner=user, status=MeetingStatus.REPORT_PENDING)

    deleted = MeetingFactory.create(owner=user, status=MeetingStatus.DELETED)

    results = get_meetings_by_user_id(user_id=1)

    print({m.user_id for m in [active1, active2, deleted]})

    assert deleted.id not in {m.id for m in results}

    assert {m.id for m in results} == {active1.id, active2.id}
