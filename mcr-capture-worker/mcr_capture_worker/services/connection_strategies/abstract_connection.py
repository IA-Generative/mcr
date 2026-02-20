import asyncio
import tempfile
from abc import ABC, abstractmethod
from io import BytesIO
from loguru import logger
from playwright.async_api import BrowserContext, Page

from mcr_capture_worker.models.meeting_model import Meeting
from mcr_capture_worker.services.s3_service import put_file_in_trace_folder

MAX_RETRIES = 30
MAX_WAIT_FOR_OR_VIDEO_AUDIO = 60_000


class ConnectionStrategy(ABC):
    async def connect(
        self, page: Page, context: BrowserContext, meeting: Meeting
    ) -> None:
        try:
            await context.tracing.start(screenshots=True, snapshots=True)

            await self.connect_to_meeting(page, meeting)
            logger.info("Connected to the page")

            await self.set_bot_name(page, meeting)
            logger.info("Bot name has been set")

            await self.join_waiting_room_and_set_devices(page)
            await self.wait_for_webRTC_connection(page)
            logger.info("Bot ready!")
        except Exception:
            logger.error(
                "Couldn't connect to meeting {}, on platform: {}",
                meeting.id,
                meeting.name_platform,
            )

            trace_content = await self.stop_trace_and_get_content(context)

            await put_file_in_trace_folder(trace_content, meeting.id, "trace.zip")
            raise
        else:
            await context.tracing.stop()

    async def stop_trace_and_get_content(self, context: BrowserContext) -> BytesIO:
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmpfile:
            tmp_path = tmpfile.name
            await context.tracing.stop(path=tmp_path)
            tmpfile.seek(0)

            return BytesIO(tmpfile.read())

    @abstractmethod
    async def connect_to_meeting(self, page: Page, meeting: Meeting) -> None:
        pass

    @abstractmethod
    async def set_bot_name(self, page: Page, meeting: Meeting) -> None:
        pass

    @abstractmethod
    async def join_waiting_room_and_set_devices(self, page: Page) -> None:
        pass

    @abstractmethod
    async def load_recording_script(self, page: Page) -> None:
        pass

    def get_agent_name(self, meeting: Meeting) -> str:
        email = meeting.owner.email

        return f"FCR Agent de {email}"

    async def wait_for_webRTC_connection(self, page: Page) -> None:
        try:
            await page.wait_for_selector(
                "audio, video", timeout=MAX_WAIT_FOR_OR_VIDEO_AUDIO, state="attached"
            )
            logger.info("Found audio or video element")

            await self.wait_for_audio_stream(page)

        except TimeoutError:
            logger.error(
                "Timed out waiting for WebRTC connection (no <audio> or <video> detected)"
            )
            raise

    async def wait_for_audio_stream(self, page: Page) -> None:
        for nb_retry in range(MAX_RETRIES):
            stream_exists = await page.evaluate("window.canAcquireAudioStream()")

            if stream_exists:
                logger.info("Found WebRTC stream")
                break
            logger.info("Couldn't find audioStream: {}", nb_retry)
            await asyncio.sleep(0.5)
        else:
            raise TimeoutError("Audio element has no MediaStream attached")
