from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from pydantic import UUID4

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.feedback_schema import Feedback, FeedbackRequest
from mcr_gateway.app.services.meeting_service import MCRCoreCustomAuth
from mcr_gateway.app.utils.core_http_client import core_client
from mcr_gateway.app.utils.upstream_errors import relay_upstream_errors


@asynccontextmanager
async def get_feedback_http_client(
    user_keycloak_uuid: UUID4,
    access_token: str | None = None,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    client = core_client(
        base_url=settings.FEEDBACK_SERVICE_URL,
        auth=MCRCoreCustomAuth(user_keycloak_uuid, access_token),
    )
    try:
        yield client
    finally:
        await client.aclose()


@relay_upstream_errors("create feedback")
async def create_feedback_service(
    feedback_data: FeedbackRequest, user_keycloak_uuid: UUID4
) -> Feedback:
    """
    Service to create a new meeting.

    Args:
        feedback_data (FeedbackRequest): The data required to create a new feedback.

    Returns:
        Feedback: The newly created feedback object.
    """
    feedback_data_dict = feedback_data.model_dump()
    async with get_feedback_http_client(user_keycloak_uuid) as client:
        # TODO: This would be clearer with the slash not included in the base url
        # To make that change, one would need to change all of the services urls
        response = await client.post("", json=feedback_data_dict)
        response.raise_for_status()
        result = response.json()
        return Feedback(**result)
