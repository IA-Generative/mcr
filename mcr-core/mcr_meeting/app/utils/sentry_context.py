import asyncio
from typing import TypedDict

import sentry_sdk
from loguru import logger

from mcr_meeting.app.client.meeting_client import MeetingApiClient


class MeetingContext(TypedDict):
    meeting_id: int
    owner_keycloak_uuid: str
    name_platform: str | None


def gather_meeting_context(
    meeting_id: int, owner_keycloak_uuid: str, client: MeetingApiClient
) -> MeetingContext:
    name_platform: str | None = None
    try:
        meeting = asyncio.run(client.get_meeting(meeting_id))
        name_platform = meeting.name_platform
    except Exception:
        logger.warning(
            "Failed to fetch meeting {} details for Sentry context, using partial context",
            meeting_id,
        )

    return MeetingContext(
        meeting_id=meeting_id,
        owner_keycloak_uuid=owner_keycloak_uuid,
        name_platform=name_platform,
    )


def set_sentry_meeting_context(meeting_context: MeetingContext) -> None:
    sentry_sdk.set_tag("meeting_id", meeting_context["meeting_id"])
    sentry_sdk.set_user({"id": meeting_context["owner_keycloak_uuid"]})
    if meeting_context["name_platform"] is not None:
        sentry_sdk.set_tag("name_platform", meeting_context["name_platform"])
