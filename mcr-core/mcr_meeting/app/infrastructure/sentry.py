import asyncio
from typing import TypedDict

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.celery import CeleryIntegration

from mcr_meeting.app.configs.base import SentrySettings, Settings
from mcr_meeting.app.infrastructure.meeting_api_client import MeetingApiClient


def init_sentry() -> None:
    sentry_settings = SentrySettings()
    settings = Settings()

    try:
        sentry_sdk.init(
            dsn=sentry_settings.SENTRY_TRANSCRIPTION_DSN,
            send_default_pii=sentry_settings.SEND_DEFAULT_PII,
            traces_sample_rate=sentry_settings.TRACES_SAMPLE_RATE,
            environment=settings.ENV_MODE,
            ignore_errors=[],
            integrations=[CeleryIntegration()],
            include_local_variables=False,
        )
    except Exception as e:
        logger.warning("Sentry initialization failed, continuing without it: {}", e)


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
    sentry_sdk.set_tag("meeting.id", meeting_context["meeting_id"])
    sentry_sdk.set_user({"id": meeting_context["owner_keycloak_uuid"]})
    if meeting_context["name_platform"] is not None:
        sentry_sdk.set_tag("meeting.platform", meeting_context["name_platform"])
