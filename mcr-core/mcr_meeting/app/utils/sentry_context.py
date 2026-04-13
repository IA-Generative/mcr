import sentry_sdk

from mcr_meeting.app.schemas.meeting_schema import MeetingResponse


def set_sentry_meeting_context(
    meeting: MeetingResponse, owner_keycloak_uuid: str
) -> None:
    sentry_sdk.set_tag("meeting_id", meeting.id)
    sentry_sdk.set_tag("name_platform", meeting.name_platform)
    sentry_sdk.set_user({"id": owner_keycloak_uuid})
