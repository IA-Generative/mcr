from fastapi import status

from mcr_meeting.app.models import MeetingStatus, User
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from tests.api.conftest import PrefixedTestClient
from tests.factories.meeting_factory import MeetingFactory


def _auth_header(user: User) -> dict[str, str]:
    return {"X-User-keycloak-uuid": str(user.keycloak_uuid)}


def test_init_capture_success(
    meeting_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.NONE,
        name_platform=MeetingPlatforms.COMU,
    )
    headers = _auth_header(user_fixture)

    # Act
    response = meeting_client.post(f"/{meeting.id}/capture/init", headers=headers)

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = meeting_client.get(f"/{meeting.id}", headers=headers)
    assert get_response.json()["status"] == MeetingStatus.CAPTURE_PENDING


def test_stop_capture_success(
    meeting_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )
    headers = _auth_header(user_fixture)

    # Act
    response = meeting_client.post(f"/{meeting.id}/capture/stop", headers=headers)

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = meeting_client.get(f"/{meeting.id}", headers=headers)
    assert get_response.json()["status"] == MeetingStatus.CAPTURE_DONE


def test_init_capture_illegal_transition_returns_409(
    meeting_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )
    headers = _auth_header(user_fixture)

    # Act
    response = meeting_client.post(f"/{meeting.id}/capture/init", headers=headers)

    # Assert
    assert response.status_code == status.HTTP_409_CONFLICT
