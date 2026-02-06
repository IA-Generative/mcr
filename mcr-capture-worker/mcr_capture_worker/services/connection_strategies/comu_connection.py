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
        await page.locator('input[name="cma_join_meeting_id_uri"]').fill(
            meeting.meeting_platform_id,
        )
        await page.locator('input[name="cma_join_meeting_passcode"]').fill(
            meeting.meeting_password,
        )
        await page.get_by_role("button", name="Join meeting").click()

    async def set_bot_name(self, page: Page, meeting: Meeting) -> None:
        await page.locator('input[name="cma_display_name_input"]').fill(
            self.get_agent_name(meeting),
        )
        await page.get_by_role("button", name="Set display name").click()

    async def join_waiting_room_and_set_devices(self, page: Page) -> None:
        await self.set_camera_and_mic_off(page)
        await self.join_waiting_room(page)

    async def join_waiting_room(self, page: Page) -> None:
        await page.get_by_role("button", name="Join meeting").click()

    async def set_camera_and_mic_off(self, page: Page) -> None:
        await page.get_by_role("button", name="Video enabled").click()
        await page.get_by_role("button", name="Microphone enabled").click()

    async def load_recording_script(self, page: Page) -> None:
        await page.add_init_script(
            path="mcr_capture_worker/services/audio/webinaire_comu/audioRecorder.js"
        )
