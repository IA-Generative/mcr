from pydantic import UUID4

from mcr_meeting.app.db.user_repository import (
    get_user_by_keycloak_uuid,
    save_user,
)
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models import User
from mcr_meeting.app.schemas.user_schema import (
    UserCreate,
)


def create_user_service(user_data: UserCreate) -> User:
    """
    Service to create a new user.

    Args:
        user (User): The user object to be created.

    Returns:
        User: The created user object with updated information (e.g., ID).
    """
    user_orm = User(**user_data.model_dump(exclude_unset=True))
    return save_user(user_orm)


def get_user_by_keycloak_uuid_service(user_keycloak_uuid: UUID4) -> User:
    """
    Service to get a user by keycloak_uuid.
    """
    return get_user_by_keycloak_uuid(user_keycloak_uuid)


def get_or_create_user_by_keycloak_uuid_service(user_create: UserCreate) -> User:
    """
    Service to get a user by keycloak_uuid, or create one if not found.
    """
    try:
        return get_user_by_keycloak_uuid(user_create.keycloak_uuid)
    except NotFoundException:
        return create_user_service(user_create)
