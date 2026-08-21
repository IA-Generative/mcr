import httpx
from fastapi import HTTPException, status
from loguru import logger

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.user_schema import (
    User,
    UserCreate,
)
from mcr_gateway.app.utils.core_http_client import core_client


async def get_or_create_user_by_keycloak_uuid_service(user_create: UserCreate) -> User:
    """
    Service to get a user or create one if not found.

    Args:
        user_create (UserCreate): The data to create the user if not found.

    Returns:
        User: The user corresponding to the provided Keycloak data.
    """
    try:
        async with core_client() as client:
            url = f"{settings.USER_SERVICE_URL}get-or-create-by-keycloak"
            response = await client.post(url, json=user_create.model_dump(mode="json"))
            response.raise_for_status()
            return User(**response.json())
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error during user creation: {} - {}",
            e.response.status_code,
            e.response.text,
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error during user creation: {}", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )
