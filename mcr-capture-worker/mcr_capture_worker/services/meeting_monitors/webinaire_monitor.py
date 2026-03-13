from loguru import logger
from playwright.async_api import Page

from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
    MeetingMonitor,
)


class WebinaireMeetingMonitor(MeetingMonitor):
    async def _get_participant_count(self, page: Page) -> int:
        user_count_span = page.locator("[data-test-users-count]")
        count_str = await user_count_span.get_attribute(
            "data-test-users-count", timeout=5000
        )
        if count_str is None:
            raise ValueError("data-test-users-count attribute not found")
        return int(count_str)

    async def enforce_bot_muted(self, page: Page) -> None:
        mute_button = page.locator("[data-test='muteMicButton']")

        if await mute_button.count() > 0:
            logger.info("Bot mic was activated by a participant — muting")
            await mute_button.click()