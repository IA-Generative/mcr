import asyncio

from loguru import logger
from playwright.async_api import Page, TimeoutError

from mcr_capture_worker.models.meeting_model import Meeting
from mcr_capture_worker.schemas.meeting_schema import is_meeting_with_url
from mcr_capture_worker.services.connection_strategies.abstract_connection import (
    ConnectionStrategy,
)
from mcr_capture_worker.settings.settings import CaptureSettings

capture_settings = CaptureSettings()


class WebinaireConnectionStrategy(ConnectionStrategy):
    async def connect_to_meeting(self, page: Page, meeting: Meeting) -> None:
        if not is_meeting_with_url(meeting):
            raise ValueError("Webinaire meeting doesn't have a valid url")

        await page.goto(meeting.url)

    async def set_bot_name(self, page: Page, meeting: Meeting) -> None:
        await page.fill(
            'xpath=//*[@id="fullname"]',
            self.get_agent_name(meeting),
        )

    async def join_waiting_room_and_set_devices(self, page: Page) -> None:
        await self.join_meeting(page)

        for nb_tries in range(capture_settings.MAX_RETRIES):
            confirm_setting_success = await self.confirm_mic_settings_button(page)

            if confirm_setting_success:
                break

            await self.accept_recording_in_progress(page)

            await asyncio.sleep(capture_settings.RETRY_DELAY)
            logger.info("Couldn't confirm settings - {}", nb_tries)
        else:
            raise TimeoutError("Couldn't set devices")

    async def join_meeting(self, page: Page) -> None:
        await page.click('xpath=//*[@id="joinMeetingForm"]/div/div[2]/div/button')

    async def confirm_mic_settings_button(self, page: Page) -> bool:
        modal = page.locator("#simpleModal")
        try:
            button_locator = modal.get_by_role(
                "button", name="Join Audio", disabled=False
            )
        except TimeoutError:
            return False

        if await button_locator.count() == 0:
            return False

        await button_locator.click()
        return True

    async def accept_recording_in_progress(self, page: Page) -> bool:
        modal = page.locator("#simpleModal")
        try:
            button_locator = modal.get_by_role(
                "button", name="Accept recording and continue"
            )
        except TimeoutError:
            return False

        if await button_locator.count() == 0:
            return False

        await button_locator.click()
        logger.info("Accepted recording!")
        return True

    async def load_recording_script(self, page: Page) -> None:
        await page.add_init_script(
            path="mcr_capture_worker/services/audio/webinaire_comu/audioRecorder.js"
        )
