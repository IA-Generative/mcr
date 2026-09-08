from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.user_schema import (
    User,
    UserCreate,
)
from mcr_gateway.app.utils.core_http_client import core_client
from mcr_gateway.app.utils.upstream_errors import relay_upstream_errors


@relay_upstream_errors("get or create user by keycloak uuid")
async def get_or_create_user_by_keycloak_uuid_service(user_create: UserCreate) -> User:
    """
    Service to get a user or create one if not found.

    Args:
        user_create (UserCreate): The data to create the user if not found.

    Returns:
        User: The user corresponding to the provided Keycloak data.
    """
    async with core_client() as client:
        url = f"{settings.USER_SERVICE_URL}get-or-create-by-keycloak"
        response = await client.post(url, json=user_create.model_dump(mode="json"))
        response.raise_for_status()
        return User(**response.json())
