import asyncio

from loguru import logger
from playwright.async_api import Page

from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
    MeetingMonitor,
)


class WebConfMeetingMonitor(MeetingMonitor):
    async def disconnect_from_meeting(self, page: Page) -> None:
        try:
            await page.click('[aria-label="Quitter la conversation"]')
            logger.info("Clicked 'Quitter la conversation'")
            await asyncio.sleep(1)
        except Exception:
            logger.warning(
                "WebConf disconnect button not found; proceeding to close browser"
            )

    async def _get_participant_count(self, page: Page) -> int:
        badge = page.locator('span[class$="-badge"]')
        text = await badge.text_content(timeout=5000)
        if text is None or not text.strip().isdigit():
            raise ValueError(f"Could not read participant count from badge: {text}")
        return int(text.strip())