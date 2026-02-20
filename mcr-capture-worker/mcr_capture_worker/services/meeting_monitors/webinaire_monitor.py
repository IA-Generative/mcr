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
