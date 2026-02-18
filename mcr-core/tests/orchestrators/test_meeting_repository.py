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

    results = get_meetings(
        user_keycloak_uuid=user.keycloak_uuid, search=None, page=1, page_size=10
    )

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

    results = get_meetings(
        user_keycloak_uuid=user.keycloak_uuid, search="min_int", page=1, page_size=10
    )

    assert deleted.id not in {m.id for m in results}

    assert {m.id for m in results} == {active1.id, active2.id}


def test_get_meetings_pagination_defaults():
    user = UserFactory.create()

    MeetingFactory.create_batch(15, owner=user, status=MeetingStatus.IMPORT_PENDING)

    results = get_meetings(
        user_keycloak_uuid=user.keycloak_uuid, search=None, page=1, page_size=10
    )

    assert len(results) == 10


def test_get_meetings_pagination_page_2():
    user = UserFactory.create()

    MeetingFactory.create_batch(15, owner=user, status=MeetingStatus.IMPORT_PENDING)

    results = get_meetings(
        user_keycloak_uuid=user.keycloak_uuid, search=None, page=2, page_size=10
    )

    assert len(results) == 5


def test_get_meetings_pagination_custom_page_size():
    user = UserFactory.create()

    MeetingFactory.create_batch(15, owner=user, status=MeetingStatus.IMPORT_PENDING)

    results = get_meetings(
        user_keycloak_uuid=user.keycloak_uuid, search=None, page=1, page_size=13
    )

    assert len(results) == 13


def test_get_meetings_pagination_beyond_last_page():
    user = UserFactory.create()

    MeetingFactory.create_batch(5, owner=user, status=MeetingStatus.IMPORT_PENDING)

    results = get_meetings(
        user_keycloak_uuid=user.keycloak_uuid, search=None, page=100, page_size=10
    )

    assert len(results) == 0


def test_get_meetings_pagination_negative_page():
    user = UserFactory.create()

    MeetingFactory.create_batch(10, owner=user, status=MeetingStatus.IMPORT_PENDING)

    results = get_meetings(
        user_keycloak_uuid=user.keycloak_uuid, search=None, page=-1, page_size=10
    )

    # Negative page is clamped to 1, so returns results like page 1
    assert len(results) == 10


def test_get_meetings_pagination_negative_page_size():
    user = UserFactory.create()

    MeetingFactory.create_batch(12, owner=user, status=MeetingStatus.IMPORT_PENDING)

    results = get_meetings(
        user_keycloak_uuid=user.keycloak_uuid, search=None, page=1, page_size=-5
    )

    # Negative page_size is clamped to 1, so returns 1 result
    assert len(results) == 1


def test_get_meetings_pagination_with_search():
    user = UserFactory.create()

    MeetingFactory.create_batch(
        15, owner=user, name="pagination_test", status=MeetingStatus.IMPORT_PENDING
    )

    MeetingFactory.create(
        owner=user, name="other_meeting", status=MeetingStatus.IMPORT_PENDING
    )

    results = get_meetings(
        user_keycloak_uuid=user.keycloak_uuid,
        search="pagination_test",
        page=1,
        page_size=10,
    )

    assert len(results) == 10

    results_page2 = get_meetings(
        user_keycloak_uuid=user.keycloak_uuid,
        search="pagination_test",
        page=2,
        page_size=10,
    )

    assert len(results_page2) == 5
