import asyncio

from loguru import logger
from playwright.async_api import Page

from mcr_capture_worker.models.meeting_model import Meeting
from mcr_capture_worker.schemas.meeting_schema import is_meeting_with_url
from mcr_capture_worker.services.connection_strategies.abstract_connection import (
    ConnectionStrategy,
)
from mcr_capture_worker.settings.settings import CaptureSettings

capture_settings = CaptureSettings()


class WebConfConnectionStrategy(ConnectionStrategy):
    CONNECTION_TIMEOUT = 300000  # 5 minutes in milliseconds

    async def connect_to_meeting(self, page: Page, meeting: Meeting) -> None:
        if not is_meeting_with_url(meeting):
            raise ValueError("WebConf meeting doesn't have a valid url")

        await page.goto(meeting.url)

    async def set_bot_name(self, page: Page, meeting: Meeting) -> None:
        await page.wait_for_selector(
            "#premeeting-name-input", state="visible", timeout=self.CONNECTION_TIMEOUT
        )
        await page.fill(
            "#premeeting-name-input",
            self.get_agent_name(meeting),
        )

    async def join_waiting_room_and_set_devices(self, page: Page) -> None:
        await self.join_meeting(page)
        await self.disable_camera_and_microphone(page)

        # Wait for the meeting interface to be ready
        await asyncio.sleep(5)

        logger.info("Meeting interface loaded successfully")

    async def wait_for_webRTC_connection(self, page: Page) -> None:
        logger.info(
            "WEBCONF: Skipping MediaStream check (will be available when participants speak)"
        )

    async def join_meeting(self, page: Page) -> None:
        join_button_selector = '[data-testid="prejoin.joinMeeting"]'
        await page.click(join_button_selector)
        logger.info("Clicked join button")

    async def disable_camera_and_microphone(self, page: Page) -> None:
        await page.click('[aria-label="Couper votre vidéo"]')
        await page.click('[aria-label="Couper votre micro"]')
        logger.info("Disabled camera and microphone")

    async def load_recording_script(self, page: Page) -> None:
        await page.add_init_script(
            path="mcr_capture_worker/services/audio/webconf/config.js"
        )
        await page.add_init_script(
            path="mcr_capture_worker/services/audio/webconf/streamUtils.js"
        )
        await page.add_init_script(
            path="mcr_capture_worker/services/audio/webconf/recorderController.js"
        )
        await page.add_init_script(
            path="mcr_capture_worker/services/audio/webconf/index.js"
        )
