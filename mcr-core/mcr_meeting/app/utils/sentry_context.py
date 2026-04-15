from typing import TypedDict

import sentry_sdk


class MeetingContext(TypedDict):
    meeting_id: int
    owner_keycloak_uuid: str
    name_platform: str | None


def set_sentry_meeting_context(meeting_context: MeetingContext) -> None:
    sentry_sdk.set_tag("meeting_id", meeting_context["meeting_id"])
    sentry_sdk.set_user({"id": meeting_context["owner_keycloak_uuid"]})
    if meeting_context["name_platform"] is not None:
        sentry_sdk.set_tag("name_platform", meeting_context["name_platform"])
