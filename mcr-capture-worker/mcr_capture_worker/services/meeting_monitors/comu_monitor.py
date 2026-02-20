from playwright.async_api import Page

from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
    MeetingMonitor,
)


class ComuMeetingMonitor(MeetingMonitor):
    async def _get_participant_count(self, page: Page) -> int:
        count_text = await page.evaluate(
            """() => {
                const btn = document.querySelector('[data-test="participants-button"]');
                if (!btn) return null;
                const badge = btn.querySelector('mdc-badge');
                if (!badge) return null;
                return badge.shadowRoot?.textContent?.trim() ?? null;
            }"""
        )
        if count_text is None or not count_text.strip().isdigit():
            raise ValueError(f"Could not read participant count from badge: {count_text}")
        return int(count_text.strip())
