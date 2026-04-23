import asyncio
import time
from collections.abc import Awaitable, Callable
from io import BytesIO
from pathlib import Path

from loguru import logger
from playwright.async_api import ConsoleMessage, Page, async_playwright

from mcr_capture_worker.clients.meeting_transition_client import MeetingApiClient
from mcr_capture_worker.meeting_repository import get_meeting, get_meeting_with_owner
from mcr_capture_worker.models.meeting_model import Meeting, MeetingStatus
from mcr_capture_worker.schemas.audio_capture_schema import OnDataAvailableBytesWrapper
from mcr_capture_worker.services.connection_strategies.factory import (
    build_connection_strategy,
)
from mcr_capture_worker.services.meeting_monitors.factory import build_meeting_monitor
from mcr_capture_worker.services.s3_service import (
    put_file_in_audio_folder,
)
from mcr_capture_worker.services.webex_node_capture import WebexNodeCapture
from mcr_capture_worker.settings.settings import ApiSettings, CaptureSettings
from mcr_capture_worker.utils.upload_queue import UploadQueue

capture_settings = CaptureSettings()
api_settings = ApiSettings()

WEBEX_NODE_BOT_DIR = Path(__file__).parent / "audio" / "webex_node"
WEBEX_NODE_BOT_SCRIPT = WEBEX_NODE_BOT_DIR / "webex_node_bot.js"


class MeetingAudioRecorder:
    """
    Class to handle the audio capture from online meetings using Playwright.
    """

    def __init__(self, meeting_id: int):
        self.meeting_id = meeting_id
        self.pending_uploads = UploadQueue()
        self.teardown_after_stop_is_finished = False
        self.meeting_transition_client: MeetingApiClient | None = None
        self._connected_at: float | None = None

    async def start(self) -> None:
        meeting = get_meeting_with_owner(self.meeting_id)
        if meeting is None:
            raise ValueError(f"Couldn't get meeting {self.meeting_id}")

        self.user_uuid = meeting.owner.keycloak_uuid
        self.meeting_platform = meeting.name_platform

        self.meeting_transition_client = MeetingApiClient(str(self.user_uuid))
        if self.meeting_transition_client is None:
            raise RuntimeError("MeetingTransitionClient is not initialized")

        if meeting.name_platform == "WEBEX":
            await self._start_webex_node_capture(meeting)
        else:
            await self._start_playwright_capture(meeting)

    async def _start_playwright_capture(self, meeting: Meeting) -> None:
        assert self.meeting_transition_client is not None
        self.connection_strategy = build_connection_strategy(meeting)

        async with async_playwright() as playwright:
            self.browser = await playwright.chromium.launch(
                headless=capture_settings.BROWSER_HEADLESS,
                args=[
                    "--no-sandbox",
                    "--use-fake-device-for-media-stream",
                    "--use-fake-ui-for-media-stream",
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-dev-shm-usage",
                ],
            )

            context = await self.browser.new_context(
                permissions=["microphone", "camera"],
            )
            page = await context.new_page()
            page.set_default_timeout(capture_settings.TIMEOUT_INDIVIDUAL_BOT_ACTION_MS)

            page.on("console", self.handle_console_message)

            self.meeting_monitor = build_meeting_monitor(meeting, page)

            await self.load_recording_script(page)
            await self.connection_strategy.connect(page, context, meeting)
            await self.connection_strategy.post_connect_setup(page)
            self._connected_at = time.monotonic()

            await self.meeting_transition_client.start_capture_bot(self.meeting_id)

            await context.expose_function(
                "sendOnDataavailableToWorker", self.handle_data_available
            )
            await context.expose_function("sendOnStartToWorker", self.handle_start)
            await context.expose_function("sendOnStopToWorker", self.handle_stop)
            time.sleep(3)

            await self.start_recording(page)
            await self.wait_for_data_or_meeting_end(page)

    async def _start_webex_node_capture(self, meeting: Meeting) -> None:
        assert self.meeting_transition_client is not None

        def handle_chunk(payload: bytes) -> None:
            self.pending_uploads.append(self.handle_audio_chunk(BytesIO(payload)))

        capture = WebexNodeCapture(
            meeting=meeting,
            meeting_transition_client=self.meeting_transition_client,
            script_path=WEBEX_NODE_BOT_SCRIPT,
            on_chunk=handle_chunk,
            on_connected=self._mark_connected,
        )
        self.meeting_monitor = capture.monitor

        await capture.run(poll_fn=self._poll_until_stop)

        # Finalize — upload any pending chunks and transition state
        await self.end_capture_if_in_progress()
        await self.pending_uploads.wait_for_all_to_finish()
        logger.info("WEBEX NODE: all chunks uploaded, initiating transcription")
        await self.meeting_transition_client.init_transcription(self.meeting_id)

    def _mark_connected(self) -> None:
        self._connected_at = time.monotonic()

    async def _poll_until_stop(
        self, stop_callback: Callable[[], Awaitable[None]]
    ) -> None:
        """Poll DB status and auto-disconnect conditions every second.

        Calls stop_callback once when either trigger fires, then returns.
        """
        while True:
            meeting = get_meeting(self.meeting_id)
            if not meeting or meeting.status != MeetingStatus.CAPTURE_IN_PROGRESS:
                await stop_callback()
                return

            if await self._should_auto_disconnect():
                logger.info(
                    "Auto-disconnecting from meeting {} -- bot has been alone for {} seconds",
                    self.meeting_id,
                    capture_settings.AUTO_DISCONNECT_GRACE_PERIOD_S,
                )
                await stop_callback()
                return

            await self.meeting_monitor.enforce_bot_muted()
            await asyncio.sleep(1)

    async def wait_for_data_or_meeting_end(self, page: Page) -> None:
        async def stop() -> None:
            await self.stop_recording(page)

        try:
            await self._poll_until_stop(stop)
        except Exception as e:
            logger.error(
                "Error in wait_for_data_or_meeting_end for meeting: {}, Error details: {}",
                self.meeting_id,
                e,
            )
            await self.browser.close()

    async def _should_auto_disconnect(self) -> bool:
        # if self._connected_at is not None:
        #     elapsed_since_connect = time.monotonic() - self._connected_at
        #     if elapsed_since_connect < capture_settings.AUTO_DISCONNECT_INITIAL_DELAY_S:
        #         return False

        # return await self.meeting_monitor.should_disconnect(
        #     capture_settings.AUTO_DISCONNECT_GRACE_PERIOD_S
        # )

        # The bot's automatic disconnection is a dysfunctional feature, it is currently disabled
        return False

    async def handle_audio_chunk(self, data: BytesIO) -> None:
        try:
            now_ts = int(time.time())
            filename = f"{now_ts}.weba"
            await asyncio.sleep(1)

            await self.meeting_monitor.enable_chunk_size_based_disconnection(data)

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
            await self.meeting_monitor.disconnect_from_meeting()
        except Exception:
            logger.error(
                "Encountered error disconnecting from meeting: {}", self.meeting_id
            )
        await self.wait_for_teardown_to_finish()
        logger.info("Recording stopped...")

    async def wait_for_teardown_to_finish(self) -> None:
        deadline = time.monotonic() + capture_settings.TEARDOWN_TIMEOUT
        while not self.teardown_after_stop_is_finished:
            if time.monotonic() >= deadline:
                logger.warning(
                    "Teardown timed out for meeting: {} — forcing browser close",
                    self.meeting_id,
                )
                await self.browser.close()
                return
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
