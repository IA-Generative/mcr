from playwright.sync_api import Page

from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
    MeetingMonitor,
)


class WebexMeetingMonitor(MeetingMonitor):
    async def enforce_bot_muted(self, page: Page) -> None:
        pass

    async def _get_participant_count(self, page: Page) -> int:
        pass
