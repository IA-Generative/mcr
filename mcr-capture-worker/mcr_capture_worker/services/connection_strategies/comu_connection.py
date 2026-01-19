from playwright.async_api import Page

from mcr_capture_worker.models.meeting_model import Meeting
from mcr_capture_worker.schemas.meeting_schema import (
    IMeetingWithPlatformAndPassword,
    IMeetingWithUrl,
    is_meeting_with_password,
    is_meeting_with_url,
)
from mcr_capture_worker.services.connection_strategies.abstract_connection import (
    ConnectionStrategy,
)


class ComuConnectionStrategy(ConnectionStrategy):
    BASE_URL = "https://webconf.comu.gouv.fr/en-US/"

    async def connect_to_meeting(self, page: Page, meeting: Meeting) -> None:
        if is_meeting_with_password(meeting):
            await self.connect_meeting_with_password(page, meeting)
        elif is_meeting_with_url(meeting):
            await self.connect_meeting_with_url(page, meeting)
        else:
            raise ValueError("Unable to connect")

    async def connect_meeting_with_url(
        self, page: Page, meeting: IMeetingWithUrl
    ) -> None:
        await page.goto(meeting.url)

    async def connect_meeting_with_password(
        self, page: Page, meeting: IMeetingWithPlatformAndPassword
    ) -> None:
        await page.goto(self.BASE_URL)
        await page.fill(
            "xpath=/html/body/div/main/section/form/div/input",
            meeting.meeting_platform_id,
        )
        await page.fill(
            "xpath=/html/body/div/main/section/form/input[3]",
            meeting.meeting_password,
        )
        await page.click("xpath=/html/body/div/main/section/form/button")

    async def set_bot_name(self, page: Page, meeting: Meeting) -> None:
        await page.fill(
            "xpath=/html/body/div/section/section/section[1]/form/input",
            self.get_agent_name(meeting),
        )
        await page.click("xpath=/html/body/div/section/section/section[1]/form/button")

    async def join_waiting_room_and_set_devices(self, page: Page) -> None:
        await self.set_camera_and_mic_off(page)
        await self.join_waiting_room(page)

    async def join_waiting_room(self, page: Page) -> None:
        await page.click("xpath=/html/body/div/section/section/section/button[1]")

    async def set_camera_and_mic_off(self, page: Page) -> None:
        await page.click('//*[@id="meeting_app"]/section[1]/section/section/button[2]')
        await page.click('//*[@id="meeting_app"]/section[1]/section/section/button[3]')

    async def load_recording_script(self, page: Page) -> None:
        await page.add_init_script(
            path="mcr_capture_worker/services/audio/webinaire_comu/audioRecorder.js"
        )
