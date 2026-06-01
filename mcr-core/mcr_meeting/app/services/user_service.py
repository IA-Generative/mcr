from pydantic import UUID4

from mcr_meeting.app.db.user_repository import get_user_by_keycloak_uuid
from mcr_meeting.app.models import User


def get_user_by_keycloak_uuid_service(user_keycloak_uuid: UUID4) -> User:
    """
    Service to get a user by keycloak_uuid.
    """
    return get_user_by_keycloak_uuid(user_keycloak_uuid)
