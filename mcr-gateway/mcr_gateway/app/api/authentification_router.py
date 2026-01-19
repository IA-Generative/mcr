from fastapi import APIRouter, Depends, HTTPException, status

from mcr_gateway.app.schemas.user_schema import (
    Role,
    TokenUser,
    User,
    UserCreate,
)
from mcr_gateway.app.services.authentification_service import (
    authorize_user,
)
from mcr_gateway.app.services.user_service import (
    get_or_create_user_by_keycloak_uuid_service,
)

router = APIRouter()


@router.get("/me", response_model=User, tags=["Authentification"])
async def get_or_create_current_user(
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> User:
    """
    Endpoint to get current user

    Returns:
        TokenUser: user data
    """
    try:
        user_create = UserCreate(
            keycloak_uuid=current_user.keycloak_uuid,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            entity_name=current_user.entity_name,
            email=current_user.email,
        )
        db_user = await get_or_create_user_by_keycloak_uuid_service(user_create)
        return db_user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error when getting or creating user",
        )
