from io import BytesIO

from loguru import logger
from playwright.async_api import Page

from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
    MeetingMonitor,
)


class WebinaireMeetingMonitor(MeetingMonitor):
    def __init__(self, page: Page) -> None:
        super().__init__()
        self._page = page

    async def _get_participant_count(self) -> int:
        user_count_span = self._page.locator("[data-test-users-count]")
        count_str = await user_count_span.get_attribute(
            "data-test-users-count", timeout=5000
        )
        if count_str is None:
            raise ValueError("data-test-users-count attribute not found")
        return int(count_str)

    async def enforce_bot_muted(self) -> None:
        mute_button = self._page.locator("[data-test='muteMicButton']")

        if await mute_button.count() > 0:
            logger.info("Bot mic was activated by a participant — muting")
            await mute_button.click()

    async def enable_chunk_size_based_disconnection(self, data: BytesIO) -> None:
        return
