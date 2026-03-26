from asyncio import sleep

from loguru import logger
from playwright.async_api import Page

from mcr_capture_worker.models.meeting_model import Meeting
from mcr_capture_worker.schemas.meeting_schema import is_meeting_with_url
from mcr_capture_worker.services.connection_strategies.abstract_connection import (
    ConnectionStrategy,
)


class WebexStrategy(ConnectionStrategy):
    MEETING_IFRAME_ID = "#unified-webclient-iframe"

    def _meeting_frame(self, page: Page):
        return page.frame_locator(self.MEETING_IFRAME_ID)

    async def connect_to_meeting(self, page: Page, meeting: Meeting) -> None:
        if not is_meeting_with_url(meeting):
            raise ValueError("Visio meeting doesn't have a valid url")

        await page.goto(meeting.url, wait_until="domcontentloaded")
        try:
            await self._select_webex_browser_version(page)
        except:
            pass
        await self._dismiss_cookie_banner(page)

    async def set_bot_name(self, page, meeting):
        frame = self._meeting_frame(page)
        locator = frame.locator("input[autocomplete='name']")
        await locator.wait_for(state="visible", timeout=30000)
        await locator.fill(self.get_agent_name(meeting))

    async def join_waiting_room_and_set_devices(self, page):
        frame = self._meeting_frame(page)
        locator = frame.locator("#join-button")
        await locator.wait_for(state="visible", timeout=30000)
        await locator.click()
        await sleep(2)

    async def wait_for_webRTC_connection(self, page: Page) -> None:
        logger.info(
            "WEBEX2: Skipping page-level MediaStream check (audio/video elements are inside the iframe)"
        )

    async def load_recording_script(self, page: Page) -> None:
        await page.add_init_script(
            path="mcr_capture_worker/services/audio/wait_for_stream_strategy/audioRecorder.js"
        )

    async def _dismiss_cookie_banner(self, page: Page):
        try:
            reject_button = page.get_by_role("button", name="Reject")
            await reject_button.wait_for(state="visible", timeout=5000)
            await reject_button.click()
            logger.info("WEBEX: Cookie banner dismissed")
        except Exception:
            logger.info("WEBEX: No cookie banner found, continuing")

    async def _select_webex_browser_version(self, page: Page):
        locator = page.get_by_role("button", name="Join from this browser")
        await locator.wait_for(state="visible", timeout=20000)
        await locator.click()

    async def _give_no_permissions(self, page: Page):
        locator = page.get_by_role(
            "button", name="Continue without microphone and camera"
        )
        await locator.wait_for(state="visible", timeout=20000)
        await locator.click()

    async def _choose_no_microphone(self, page: Page):
        locator = page.get_by_role("button", name="Continue without microphone")
        await locator.wait_for(state="visible", timeout=20000)
        await locator.click()
