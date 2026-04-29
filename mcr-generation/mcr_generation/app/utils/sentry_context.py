from typing import TypedDict

import sentry_sdk
from loguru import logger

from mcr_generation.app.client.meeting_client import MeetingApiClient


class MeetingContext(TypedDict):
    meeting_id: int
    owner_keycloak_uuid: str | None
    name_platform: str | None


def gather_meeting_context(
    meeting_id: int,
    owner_keycloak_uuid: str | None,
    client: MeetingApiClient,
) -> MeetingContext:
    if owner_keycloak_uuid is None:
        logger.warning(
            "No owner_keycloak_uuid for meeting {}; skipping meeting fetch "
            "(legacy task format — Sentry context will be partial)",
            meeting_id,
        )
        return MeetingContext(
            meeting_id=meeting_id,
            owner_keycloak_uuid=None,
            name_platform=None,
        )

    name_platform: str | None = None
    try:
        meeting = client.get_meeting(meeting_id)
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
    sentry_sdk.set_tag("meeting.id", meeting_context["meeting_id"])
    if meeting_context["owner_keycloak_uuid"] is not None:
        sentry_sdk.set_user({"id": meeting_context["owner_keycloak_uuid"]})
    if meeting_context["name_platform"] is not None:
        sentry_sdk.set_tag("meeting.platform", meeting_context["name_platform"])
