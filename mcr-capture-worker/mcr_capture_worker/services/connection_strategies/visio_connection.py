from playwright.async_api import Page

from mcr_capture_worker.models.meeting_model import Meeting
from mcr_capture_worker.schemas.meeting_schema import (
    is_meeting_with_url,
)
from mcr_capture_worker.services.connection_strategies.abstract_connection import (
    ConnectionStrategy,
)


class VisioStrategy(ConnectionStrategy):
    async def connect_to_meeting(self, page: Page, meeting: Meeting) -> None:
        if not is_meeting_with_url(meeting):
            raise ValueError("Visio meeting doesn't have a valid url")

        await page.goto(meeting.url)

    async def set_bot_name(self, page: Page, meeting: Meeting) -> None:
        await page.locator('input[autocomplete="name"]').fill(
            self.get_agent_name(meeting)
        )

    async def join_waiting_room_and_set_devices(self, page: Page) -> None:
        await self._set_camera_and_mic_off(page)
        await self._join_waiting_room(page)

    async def load_recording_script(self, page: Page) -> None:
        await page.add_init_script(
            path="mcr_capture_worker/services/audio/webinaire_comu/audioRecorder.js"
        )

    async def _join_waiting_room(self, page: Page) -> None:
        await page.get_by_role("button", name="Join").click()

    async def _set_camera_and_mic_off(self, page: Page) -> None:
        await page.get_by_role("button", name="Disable microphone").click()
        await page.get_by_role("button", name="Disable camera").click()
