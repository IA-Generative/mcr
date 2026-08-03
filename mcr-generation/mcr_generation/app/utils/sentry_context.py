import logging  # noqa: TID251
from typing import TypedDict

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration

from mcr_generation.app.client.meeting_client import MeetingApiClient
from mcr_generation.app.configs.settings import SentrySettings


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


def init_sentry() -> None:
    sentry_settings = SentrySettings()
    try:
        sentry_sdk.init(
            dsn=sentry_settings.SENTRY_GENERATION_DSN,
            send_default_pii=sentry_settings.SEND_DEFAULT_PII,
            traces_sample_rate=sentry_settings.TRACES_SAMPLE_RATE,
            environment=sentry_settings.ENV_MODE,
            ignore_errors=[],
            integrations=[CeleryIntegration(), *_logging_integrations()],
        )
    except Exception as e:
        logger.warning("Sentry initialization failed, continuing without it: {}", e)


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
