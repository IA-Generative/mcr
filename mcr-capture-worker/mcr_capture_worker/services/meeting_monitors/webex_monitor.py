import re

from loguru import logger
from playwright.async_api import FrameLocator, Page

from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
    MeetingMonitor,
)


class WebexMeetingMonitor(MeetingMonitor):
    MEETING_IFRAME_ID = "#unified-webclient-iframe"
    PARTICIPANTS_TOGGLE_BUTTON_SELECTOR = "[data-test='participants-toggle-button']"

    def __init__(self, page: Page) -> None:
        super().__init__()
        self._page = page

    def _get_meeting_frame(self) -> FrameLocator:
        return self._page.frame_locator(self.MEETING_IFRAME_ID)

    async def _get_participant_count(self) -> int:
        frame = self._get_meeting_frame()
        await self._ensure_participants_panel_open(frame)
        heading = frame.locator("mdc-text[tagname='h2']", has_text="Participants")
        await heading.first.wait_for(state="visible", timeout=5000)
        text = await heading.first.text_content()
        match = re.search(r"\((\d+)\)", text or "")
        if not match:
            raise ValueError(f"Could not read participant count from: {text}")
        return int(match.group(1))

    async def _ensure_participants_panel_open(self, frame: FrameLocator) -> None:
        button = frame.locator(self.PARTICIPANTS_TOGGLE_BUTTON_SELECTOR)
        aria = await button.get_attribute("aria-expanded")
        if aria == "false":
            await button.click()
            logger.info("Participants panel opened")
