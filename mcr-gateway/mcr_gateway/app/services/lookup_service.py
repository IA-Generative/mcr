from pydantic import UUID4

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.lookup_schema import (
    ComuMeetingLookup,
    ComuMeetingLookupResponse,
)
from mcr_gateway.app.services.meeting_service import MCRCoreCustomAuth
from mcr_gateway.app.utils.core_http_client import core_client
from mcr_gateway.app.utils.upstream_errors import relay_upstream_errors


@relay_upstream_errors("lookup comu meeting")
async def lookup_comu_meeting_service(
    comu_meeting_data: ComuMeetingLookup,
    user_keycloak_uuid: UUID4,
) -> ComuMeetingLookupResponse:
    async with core_client(
        base_url=settings.LOOKUP_SERVICE_URL,
        auth=MCRCoreCustomAuth(user_keycloak_uuid),
    ) as client:
        response = await client.post(
            "", json=comu_meeting_data.model_dump(exclude_none=True)
        )
        response.raise_for_status()
        return ComuMeetingLookupResponse(**response.json())
