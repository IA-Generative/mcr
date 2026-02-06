import pytest

from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models import MeetingStatus
from mcr_meeting.app.orchestrators.meeting_orchestrator import get_meeting, get_meetings
from tests.factories import MeetingFactory, UserFactory


def test_get_meeting_by_id_filters_returns_error():
    user = UserFactory.create()

    deleted = MeetingFactory.create(owner=user, status=MeetingStatus.DELETED)

    with pytest.raises(NotFoundException) as exc:
        get_meeting(meeting_id=deleted.id, user_keycloak_uuid=user.keycloak_uuid)

    assert str(exc.value) == f"Meeting not found: id={deleted.id}"


def test_get_meetings_filters_deleted():
    user = UserFactory.create()

    active1 = MeetingFactory.create(owner=user, status=MeetingStatus.IMPORT_PENDING)
    active2 = MeetingFactory.create(owner=user, status=MeetingStatus.REPORT_PENDING)

    deleted = MeetingFactory.create(owner=user, status=MeetingStatus.DELETED)

    results = get_meetings(user_keycloak_uuid=user.keycloak_uuid, search=None)

    assert deleted.id not in {m.id for m in results}

    assert {m.id for m in results} == {active1.id, active2.id}


def test_get_meetings_with_search_filters_deleted():
    user = UserFactory.create()

    active1 = MeetingFactory.create(
        owner=user, name="min_int_1", status=MeetingStatus.IMPORT_PENDING
    )
    active2 = MeetingFactory.create(
        owner=user, name="min_int_2", status=MeetingStatus.REPORT_PENDING
    )

    deleted = MeetingFactory.create(
        owner=user, name="min_int_3", status=MeetingStatus.DELETED
    )

    results = get_meetings(user_keycloak_uuid=user.keycloak_uuid, search="min_int")

    assert deleted.id not in {m.id for m in results}

    assert {m.id for m in results} == {active1.id, active2.id}
