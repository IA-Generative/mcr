from playwright.async_api import Page

from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
    MeetingMonitor,
)


class ComuMeetingMonitor(MeetingMonitor):
    def __init__(self, page: Page) -> None:
        super().__init__()
        self._page = page

    async def _get_participant_count(self) -> int:
        # COMU: the mdc-badge is inside [data-test="participants-button"]
        # Use >> to pierce the shadow DOM of mdc-badge
        badge_text = self._page.locator(
            '[data-test="participants-button"] mdc-badge >> mdc-text'
        ).first
        text = await badge_text.text_content(timeout=5000)
        if text is None or not text.strip().isdigit():
            raise ValueError(f"Could not read participant count from badge: {text}")
        return int(text.strip())

    async def should_disconnect(self, grace_period_s: int) -> bool:
        return self.is_alone_timer_expired(grace_period_s)
