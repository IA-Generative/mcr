import asyncio
import os
from time import sleep

import sentry_sdk
from loguru import logger

from mcr_capture_worker.clients.meeting_transition_client import MeetingApiClient
from mcr_capture_worker.meeting_repository import (
    get_meeting_with_owner,
    get_next_element_for_capture_and_mark_as_bot_is_connecting,
)
from mcr_capture_worker.setup.logger import setup_logging
from mcr_capture_worker.setup.sentry import setup_sentry

from .services.meeting_audio_recorder import MeetingAudioRecorder


def process_meeting() -> None:
    meeting = get_next_element_for_capture_and_mark_as_bot_is_connecting()

    if not meeting:
        return

    meeting_audio_recorder = MeetingAudioRecorder(meeting_id=meeting.id)
    meeting_audio_recorder.set_connection_strategy(meeting.get_connection_strategy())
    meeting_audio_recorder.set_meeting_monitor(meeting.get_meeting_monitor())

    meeting = get_meeting_with_owner(meeting.id)
    meeting_transition_client = MeetingApiClient(str(meeting.owner.keycloak_uuid))
    try:
        logger.info("Processing meeting {}...", meeting.id)
        asyncio.run(meeting_audio_recorder.start())
        logger.info("Meeting {} processed successfully.", meeting.id)
    except Exception as e:
        logger.error("Error processing meeting {}: {}", meeting.id, e)
        sentry_sdk.capture_exception(e)
        asyncio.run(meeting_transition_client.fail_capture_bot(meeting.id))


def main() -> None:
    setup_logging()
    setup_sentry()
    process_meeting()

    # In development mode, run the task every 2 seconds
    env_mode = os.getenv("ENV_MODE")
    if env_mode == "DEV":
        while True:
            process_meeting()
            sleep(2)


if __name__ == "__main__":
    main()
