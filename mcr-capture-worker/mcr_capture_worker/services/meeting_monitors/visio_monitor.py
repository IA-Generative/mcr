from playwright.async_api import Page

from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
    MeetingMonitor,
)


class VisioMeetingMonitor(MeetingMonitor):
    def __init__(self, page: Page) -> None:
        super().__init__()
        self._page = page

    async def _get_participant_count(self) -> int:
        # Visio: participant count in a circle badge overlay
        badge = self._page.locator("div.bdr_50\\%.bg-c_gray.c_white.fs_0\\.75rem")
        text = await badge.text_content(timeout=5000)
        if text is None or not text.strip().isdigit():
            raise ValueError(f"Could not read participant count from badge: {text}")
        return int(text.strip())

    async def should_disconnect(self, grace_period_s: int) -> bool:
        return self.is_alone_timer_expired(grace_period_s)
