import pytest
from fastapi import status
from sqlalchemy.orm import Session

from mcr_meeting.app.models import User
from mcr_meeting.app.models.feedback_model import Feedback

from .conftest import PrefixedTestClient


def _auth_header(user: User) -> dict[str, str]:
    return {"X-User-keycloak-uuid": str(user.keycloak_uuid)}


def test_create_feedback_missing_vote_type(
    feedback_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Arrange
    payload = {"url": "https://example.com"}

    # Act
    response = feedback_client.post(
        "/", json=payload, headers=_auth_header(user_fixture)
    )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_feedback_missing_url(
    feedback_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Arrange
    payload = {"vote_type": "POSITIVE"}

    # Act
    response = feedback_client.post(
        "/", json=payload, headers=_auth_header(user_fixture)
    )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("invalid_vote", ["NEUTRAL", "yes", "", 0])
def test_create_feedback_invalid_vote_type(
    feedback_client: PrefixedTestClient,
    user_fixture: User,
    invalid_vote: str | int,
) -> None:
    # Arrange
    payload = {"vote_type": invalid_vote, "url": "https://example.com"}

    # Act
    response = feedback_client.post(
        "/", json=payload, headers=_auth_header(user_fixture)
    )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_feedback_valid_payload_returns_201_and_persists(
    feedback_client: PrefixedTestClient,
    user_fixture: User,
    db_session: Session,
) -> None:
    # Arrange
    payload = {
        "vote_type": "POSITIVE",
        "url": "https://example.com/",
        "comment": "Super outil !",
    }

    # Act
    response = feedback_client.post(
        "/", json=payload, headers=_auth_header(user_fixture)
    )

    # Assert — statut HTTP
    assert response.status_code == status.HTTP_201_CREATED

    # Assert — ligne présente en DB avec le bon user_id
    feedback_id = response.json()["id"]
    db_session.expire_all()
    feedback = db_session.get(Feedback, feedback_id)
    assert feedback is not None
    assert feedback.user_id == user_fixture.id
    assert feedback.vote_type == "POSITIVE"
    assert feedback.comment == "Super outil !"


@pytest.mark.parametrize("whitespace_comment", ["   ", "\n", "   \n  ", "\t  \t"])
def test_create_feedback_whitespace_comment_stored_as_null(
    feedback_client: PrefixedTestClient,
    user_fixture: User,
    db_session: Session,
    whitespace_comment: str,
) -> None:
    # Arrange
    payload = {
        "vote_type": "NEGATIVE",
        "url": "https://example.com",
        "comment": whitespace_comment,
    }

    # Act
    response = feedback_client.post(
        "/", json=payload, headers=_auth_header(user_fixture)
    )

    # Assert — la ligne est créée
    assert response.status_code == status.HTTP_201_CREATED

    # Assert — comment est NULL en DB
    feedback_id = response.json()["id"]
    db_session.expire_all()
    feedback = db_session.get(Feedback, feedback_id)
    assert feedback is not None
    assert feedback.comment is None


def test_create_feedback_url_with_existing_meeting_stores_meeting_id(
    feedback_client: PrefixedTestClient,
    user_fixture: User,
    meeting_fixture: object,
    db_session: Session,
) -> None:
    # Arrange
    payload = {
        "vote_type": "POSITIVE",
        "url": f"https://app.example.com/meetings/{meeting_fixture.id}",
    }

    # Act
    response = feedback_client.post(
        "/", json=payload, headers=_auth_header(user_fixture)
    )

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    feedback_id = response.json()["id"]
    db_session.expire_all()
    feedback = db_session.get(Feedback, feedback_id)
    assert feedback is not None
    assert feedback.meeting_id == meeting_fixture.id


def test_create_feedback_url_with_nonexistent_meeting_stores_null(
    feedback_client: PrefixedTestClient,
    user_fixture: User,
    db_session: Session,
) -> None:
    # Arrange — meeting id 99999 n'existe pas
    payload = {
        "vote_type": "NEGATIVE",
        "url": "https://app.example.com/meetings/99999",
    }

    # Act
    response = feedback_client.post(
        "/", json=payload, headers=_auth_header(user_fixture)
    )

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    feedback_id = response.json()["id"]
    db_session.expire_all()
    feedback = db_session.get(Feedback, feedback_id)
    assert feedback is not None
    assert feedback.meeting_id is None
