from mcr_meeting.app.db.user_repository import (
    get_user_by_keycloak_uuid,
    save_user,
)
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models import User
from mcr_meeting.app.schemas.user_schema import UserCreate


def get_or_create_user_by_keycloak(user_data: UserCreate) -> User:
    """Return the user matching the keycloak_uuid, creating one if absent."""
    try:
        return get_user_by_keycloak_uuid(user_data.keycloak_uuid)
    except NotFoundException:
        return save_user(User(**user_data.model_dump(exclude_unset=True)))
