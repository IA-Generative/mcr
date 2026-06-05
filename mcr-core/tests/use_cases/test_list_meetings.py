import pytest

from mcr_meeting.app.models import User
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.use_cases.list_meetings import list_meetings
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


def test_list_meetings_returns_only_requesters_meetings(user_fixture: User) -> None:
    # Arrange
    MeetingFactory.create(owner=user_fixture, name_platform=MeetingPlatforms.COMU)
    MeetingFactory.create(owner=user_fixture, name_platform=MeetingPlatforms.COMU)
    MeetingFactory.create(name_platform=MeetingPlatforms.COMU)  # someone else

    # Act
    result = list_meetings(
        user_keycloak_uuid=user_fixture.keycloak_uuid,
        search=None,
        page=1,
        page_size=10,
    )

    # Assert
    assert result.total == 2
    assert len(result.items) == 2
    assert all(m.user_id == user_fixture.id for m in result.items)


def test_list_meetings_computes_total_pages(user_fixture: User) -> None:
    # Arrange
    for _ in range(5):
        MeetingFactory.create(owner=user_fixture, name_platform=MeetingPlatforms.COMU)

    # Act
    result = list_meetings(
        user_keycloak_uuid=user_fixture.keycloak_uuid,
        search=None,
        page=1,
        page_size=2,
    )

    # Assert
    assert result.total == 5
    assert result.total_pages == 3
    assert len(result.items) == 2


def test_list_meetings_clamps_invalid_pagination(user_fixture: User) -> None:
    # Arrange
    MeetingFactory.create(owner=user_fixture, name_platform=MeetingPlatforms.COMU)

    # Act
    result = list_meetings(
        user_keycloak_uuid=user_fixture.keycloak_uuid,
        search=None,
        page=0,
        page_size=0,
    )

    # Assert
    assert result.page == 1
    assert result.total_pages >= 1


def test_list_meetings_total_pages_is_at_least_one_when_empty(
    user_fixture: User,
) -> None:
    # Act
    result = list_meetings(
        user_keycloak_uuid=user_fixture.keycloak_uuid,
        search=None,
        page=1,
        page_size=10,
    )

    # Assert
    assert result.total == 0
    assert result.items == []
    assert result.total_pages == 1


def test_list_meetings_filters_on_search(user_fixture: User) -> None:
    # Arrange
    MeetingFactory.create(
        owner=user_fixture, name="Weekly sync", name_platform=MeetingPlatforms.COMU
    )
    MeetingFactory.create(
        owner=user_fixture, name="Retro", name_platform=MeetingPlatforms.COMU
    )

    # Act
    result = list_meetings(
        user_keycloak_uuid=user_fixture.keycloak_uuid,
        search="sync",
        page=1,
        page_size=10,
    )

    # Assert
    assert result.total == 1
    assert result.items[0].name == "Weekly sync"
