import asyncio
import time
from io import BytesIO
from typing import Optional

from loguru import logger
from playwright.async_api import ConsoleMessage, Page, async_playwright

from mcr_capture_worker.clients.meeting_transition_client import MeetingApiClient
from mcr_capture_worker.meeting_repository import get_meeting, get_meeting_with_owner
from mcr_capture_worker.models.meeting_model import MeetingStatus
from mcr_capture_worker.schemas.audio_capture_schema import OnDataAvailableBytesWrapper
from mcr_capture_worker.services.connection_strategies import (
    ConnectionStrategy,
)
from mcr_capture_worker.services.s3_service import (
    put_file_in_audio_folder,
)
from mcr_capture_worker.settings.settings import ApiSettings, CaptureSettings
from mcr_capture_worker.utils.upload_queue import UploadQueue

capture_settings = CaptureSettings()
api_settings = ApiSettings()


class MeetingAudioRecorder:
    """
    Class to handle the audio capture from online meetings using Playwright.
    """

    def __init__(self, meeting_id: int):
        self.meeting_id = meeting_id
        self.pending_uploads = UploadQueue()
        self.teardown_after_stop_is_finished = False
        self.meeting_transition_client: Optional[MeetingApiClient] = None

    def set_connection_strategy(self, connection_strategy: ConnectionStrategy) -> None:
        self.connection_strategy = connection_strategy

    async def start(self) -> None:
        """
        Captures audio from an online meeting using Playwright to automate browser actions.

        Workflow:
            1. Launches a Chromium browser instance using Playwright.
            2. Injects JavaScript scripts to record audio using a MediaRecorder.
            3. Continuously listens for data event from the injected MediaRecorder and processes them.
            4. Stops recording and closes the browser when the meeting ends or an error occurs.

        Raises:
            Exception: If any error occurs during browser automation or audio processing.
        """
        meeting = get_meeting_with_owner(self.meeting_id)
        self.user_uuid = meeting.owner.keycloak_uuid
        self.meeting_platform = meeting.name_platform

        if meeting is None:
            raise ValueError(f"Couldn't get meeting {self.meeting_id}")

        self.meeting_transition_client = MeetingApiClient(str(self.user_uuid))
        if self.meeting_transition_client is None:
            raise RuntimeError("MeetingTransitionClient is not initialized")

        async with async_playwright() as playwright:
            self.browser = await playwright.chromium.launch(
                headless=capture_settings.BROWSER_HEADLESS,
                args=[
                    "--use-fake-device-for-media-stream",
                    "--use-fake-ui-for-media-stream",
                ],
            )
            context = await self.browser.new_context(
                permissions=["microphone", "camera"],
            )
            page = await context.new_page()
            page.set_default_timeout(capture_settings.TIMEOUT_INDIVIDUAL_BOT_ACTION_MS)

            await self.load_recording_script(page)
            await self.connection_strategy.connect(page, context, meeting)

            await self.meeting_transition_client.start_capture_bot(self.meeting_id)

            page.on("console", self.handle_console_message)

            await page.expose_function(
                "sendOnDataavailableToWorker", self.handle_data_available
            )
            await page.expose_function("sendOnStartToWorker", self.handle_start)
            await page.expose_function("sendOnStopToWorker", self.handle_stop)
            time.sleep(3)

            await self.start_recording(page)
            await self.wait_for_data_or_meeting_end(page)

    async def wait_for_data_or_meeting_end(self, page: Page) -> None:
        try:
            # Check every 1 second if the transcription should be stopped
            while True:
                meeting = get_meeting(self.meeting_id)
                if not meeting or meeting.status != MeetingStatus.CAPTURE_IN_PROGRESS:
                    await self.stop_recording(page)
                    break
                # Continue capturing and processing audio chunks
                # Use asyncio.sleep instead of time.sleep to avoid blocking the event loop.
                # A blocking loop would prevent Playwright from processing browser events,
                # meaning we wouldn't receive any data from the bot's page.
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(
                "Error in wait_for_data_or_meeting_end for meeting: {}, Error details: {}",
                self.meeting_id,
                e,
            )
            await self.browser.close()

    async def handle_audio_chunk(self, data: BytesIO) -> None:
        try:
            now_ts = int(time.time())
            filename = f"{now_ts}.weba"
            await asyncio.sleep(1)

            await put_file_in_audio_folder(
                data=data,
                meeting_id=self.meeting_id,
                filename=filename,
            )

        except Exception as e:
            logger.error(
                "Error sending audio for meeting: {}, Error details: {}",
                self.meeting_id,
                e,
            )

    async def load_recording_script(self, page: Page) -> None:
        await self.connection_strategy.load_recording_script(page)

    async def start_recording(self, page: Page) -> None:
        await page.evaluate("window.startRecording()")

    def handle_console_message(self, msg: ConsoleMessage) -> None:
        try:
            filtered_msg_type = ["debug", "log"]
            if msg.type in filtered_msg_type:
                return

            logger.info("Console [{}]: {}", msg.type, msg.text)
        except Exception as e:
            logger.error(e)

    async def handle_data_available(self, data: OnDataAvailableBytesWrapper) -> None:
        self.pending_uploads.append(
            self.handle_audio_chunk(BytesIO(bytes(data["js_bytes"])))
        )

    async def handle_stop(self) -> None:
        await self.end_capture_if_in_progress()

        await asyncio.sleep(1)

        logger.info(
            "Detected change in db status - stopping recording for meeting: {}",
            self.meeting_id,
        )
        await self.pending_uploads.wait_for_all_to_finish()

        logger.info(
            "All chunk sent - Starting transcription for meeting: {}",
            self.meeting_id,
        )
        if self.meeting_transition_client is None:
            raise RuntimeError("MeetingTransitionClient is not initialized")

        await self.meeting_transition_client.init_transcription(self.meeting_id)

        logger.info(
            "Transcription initialized - starting teardown for meeting: {}",
            self.meeting_id,
        )
        await self.browser.close()
        self.mark_teardown_as_finished()

    def handle_start(self) -> None:
        logger.info("Recording started...")

    async def stop_recording(self, page: Page) -> None:
        await page.evaluate("window.stopRecording()")
        try:
            await self.connection_strategy.disconnect_from_meeting(page)
        except Exception:
            logger.error(
                "Encountered error disconnecting from meeting: {}", self.meeting_id
            )
        await self.wait_for_teardown_to_finish()
        logger.info("Recording stopped...")

    async def wait_for_teardown_to_finish(self) -> None:
        while not self.teardown_after_stop_is_finished:
            await asyncio.sleep(1)

    def mark_teardown_as_finished(self) -> None:
        logger.info("Teardown finished")
        self.teardown_after_stop_is_finished = True

    async def end_capture_if_in_progress(self) -> None:
        meeting = get_meeting_with_owner(self.meeting_id)

        if meeting is None:
            raise ValueError(f"Couldn't get meeting {self.meeting_id}")

        if self.meeting_transition_client is None:
            raise RuntimeError("MeetingTransitionClient is not initialized")

        if meeting.status == MeetingStatus.CAPTURE_IN_PROGRESS:
            await self.meeting_transition_client.end_capture(self.meeting_id)
