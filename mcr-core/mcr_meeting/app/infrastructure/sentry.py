import asyncio
import logging  # noqa: TID251
from typing import TypedDict

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration

from mcr_meeting.app.configs.base import SentrySettings, Settings
from mcr_meeting.app.infrastructure.meeting_api_client import MeetingApiClient


def _logging_integrations() -> list[Integration]:
    # A logged error is not a failure point: keep log records as breadcrumbs
    # (level=INFO) but never let them become Sentry events (event_level=None).
    # All logging funnels through loguru, so LoguruIntegration is the channel
    # that actually ships log-based events; LoggingIntegration covers the rare
    # record reaching the stdlib path directly.
    return [
        LoguruIntegration(event_level=None, level=logging.INFO),
        LoggingIntegration(event_level=None, level=logging.INFO),
    ]


def _init_sentry(
    dsn: str,
    *,
    extra_integrations: list[Integration] | None = None,
    include_local_variables: bool = True,
) -> None:

    try:
        sentry_sdk.init(
            dsn=dsn,
            send_default_pii=sentry_settings.SEND_DEFAULT_PII,
            traces_sample_rate=sentry_settings.TRACES_SAMPLE_RATE,
            environment=settings.ENV_MODE,
            ignore_errors=[],
            integrations=[*(extra_integrations or []), *_logging_integrations()],
            include_local_variables=include_local_variables,
        )
    except Exception as e:
        logger.warning("Sentry initialization failed, continuing without it: {}", e)


def init_sentry() -> None:
    _init_sentry(
        sentry_settings.SENTRY_TRANSCRIPTION_DSN,
        extra_integrations=[CeleryIntegration()],
        include_local_variables=False,
    )


def init_api_sentry() -> None:
    env_mode = settings.ENV_MODE
    if not env_mode or env_mode == "test":
        return
    _init_sentry(sentry_settings.SENTRY_CORE_DSN)


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
