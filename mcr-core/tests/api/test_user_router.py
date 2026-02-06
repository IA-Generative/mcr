from typing import Any
from uuid import uuid4

from mcr_meeting.app.models import Role, User
from mcr_meeting.app.schemas.user_schema import UserCreate

from .conftest import PrefixedTestClient


def test_get_or_create_by_keycloak_get_action(
    user_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Arrange
    user_create = UserCreate(
        first_name="Test",
        last_name="User",
        entity_name="Test",
        email="test@example.com",
        keycloak_uuid=user_fixture.keycloak_uuid,
    )
    payload = user_create.model_dump(mode="json")

    # Act
    response = user_client.post("/get-or-create-by-keycloak", json=payload)

    # Assert
    # Here we perform a get action, which means all fields of user_create other than keycloak_uuid are ignored
    json_data = response.json()
    assert response.status_code == 200
    assert json_data["keycloak_uuid"] == str(user_fixture.keycloak_uuid)


def test_get_or_create_by_keycloak_create_action(
    user_client: PrefixedTestClient,
) -> None:
    keycloak_uuid = uuid4()
    user_create = UserCreate(
        first_name="Test",
        last_name="User",
        entity_name="Test",
        email="test@example.com",
        keycloak_uuid=keycloak_uuid,
    )

    expected_result = User(**user_create.model_dump())
    expected_result.role = Role.USER
    payload = user_create.model_dump(mode="json")

    # Act
    response = user_client.post("/get-or-create-by-keycloak", json=payload)

    # Assert
    json_data = response.json()
    assert response.status_code == 200
    assert_json_equal_model(json_data, expected_result)
    assert json_data["keycloak_uuid"] == str(expected_result.keycloak_uuid)


def assert_json_equal_model(json_data: dict[str, Any], user: User) -> None:
    assert json_data["first_name"] == user.first_name
    assert json_data["last_name"] == user.last_name
    assert json_data["entity_name"] == user.entity_name
    assert json_data["email"] == user.email
    assert json_data["role"] == str(user.role)
