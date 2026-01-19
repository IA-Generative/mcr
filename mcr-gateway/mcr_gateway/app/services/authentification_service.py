from typing import Any, Callable, Coroutine, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    OAuth2PasswordBearer,
)
from keycloak import KeycloakOpenID

from mcr_gateway.app.schemas.token_schema import TokenRoles
from mcr_gateway.app.schemas.user_schema import KeycloakRole, Role, TokenUser

from ..configs.config import settings

keycloak_client = KeycloakOpenID(
    server_url=settings.KEYCLOAK_URL,
    client_id=settings.KEYCLOAK_CLIENT_ID,
    client_secret_key="",
    realm_name=settings.KEYCLOAK_REALM,
)

security = OAuth2PasswordBearer(settings.KEYCLOAK_TOKEN_URL)
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def decode_jwt_token(token: str = Depends(security)) -> TokenUser:
    """
    Authenticate the user using the JWT token.
    """
    try:
        decoded_token = keycloak_client.decode_token(token)
        token_roles = TokenRoles(**decoded_token)
        user = TokenUser(
            keycloak_uuid=decoded_token.get("sub"),
            email=decoded_token.get("email"),
            first_name=decoded_token.get("given_name"),
            entity_name="",  # TODO: remove all entity_name from app
            last_name=decoded_token.get("family_name"),
            role=get_role_from_token_roles(token_roles),
        )

        if user is None:
            raise credentials_exception
        return user
    except Exception:
        raise credentials_exception


def authorize_user(
    required_role: str,
) -> Callable[[TokenUser], Coroutine[Any, Any, TokenUser]]:
    """
    Dependency function to authorize a user based on their role.

    Args:
        required_role (str): The required role for accessing the resource.

    Returns:
        Callable: A dependency function that validates the user's role.

    Raises:
        HTTPException: If the user does not have the required permissions.
    """

    async def dependency(user: TokenUser = Depends(decode_jwt_token)) -> TokenUser:
        try:
            if user.role.value == required_role or user.role == Role.ADMIN:
                return user
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Insufficient permissions",
                )
        except HTTPException as e:
            raise e
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error when getting or creating user",
            )

    return dependency


def get_role_from_token_roles(token_roles: TokenRoles) -> Optional[Role]:
    """
    Parcourt la liste des rôles et retourne 'ADMIN' si présent, sinon 'USER' si présent, sinon None.
    """
    roles = [role.upper() for role in token_roles.get_all_roles()]
    if KeycloakRole.ADMIN.value in roles:
        return Role.ADMIN
    return Role.USER
