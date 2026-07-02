from fastapi import APIRouter, Depends

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import router_db_session_context_manager
from mcr_meeting.app.schemas.user_schema import UserCreate, UserResponse
from mcr_meeting.app.use_cases.get_or_create_user_by_keycloak import (
    get_or_create_user_by_keycloak,
)

api_settings = ApiSettings()
router = APIRouter(
    prefix=api_settings.USER_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Users"],
)


@router.post("/get-or-create-by-keycloak")
def get_or_create_user_by_keycloak_uuid(
    user_data: UserCreate,
) -> UserResponse:
    """
    Get or create a user by keycloak_uuid.

    Args:
        user_data (UserCreate): The Pydantic model containing the user data (must include keycloak_uuid).

    Returns:
        User: The user object, either existing or newly created.
    """
    user = get_or_create_user_by_keycloak(user_data)
    return UserResponse.model_validate(user)
