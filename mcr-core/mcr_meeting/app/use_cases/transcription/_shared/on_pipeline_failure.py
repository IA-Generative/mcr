import asyncio

from loguru import logger

from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException
from mcr_meeting.app.infrastructure.meeting_api_client import MeetingApiClient


def on_pipeline_failure(
    meeting_id: int,
    owner_keycloak_uuid: str,
    error_code: str,
) -> None:
    logger.info(
        "Transcription pipeline failed for meeting {} (phase: {})",
        meeting_id,
        error_code,
    )
    client = MeetingApiClient(owner_keycloak_uuid)
    try:
        asyncio.run(client.mark_transcription_as_failed(meeting_id))
    except MeetingDeletedException:
        logger.warning(
            "Meeting {} deleted; skipping TRANSCRIPTION_FAILED update", meeting_id
        )
