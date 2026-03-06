import time
from abc import ABC, abstractmethod

from loguru import logger
from playwright.async_api import Page


class MeetingMonitor(ABC):
    def __init__(self) -> None:
        self._alone_since: float | None = None

    def start_alone_timer(self) -> None:
        if self._alone_since is None:
            self._alone_since = time.monotonic()

    def reset_alone_timer(self) -> None:
        self._alone_since = None

    def is_alone_timer_expired(self, grace_period_s: int) -> bool:
        if self._alone_since is None:
            return False
        return (time.monotonic() - self._alone_since) >= grace_period_s

    async def should_disconnect(self, page: Page, grace_period_s: int) -> bool:
        """Check participant count and return True if the bot should auto-disconnect."""
        participant_count = await self.get_participant_count(page)

        if participant_count is None or participant_count <= 1:
            self.start_alone_timer()
            return self.is_alone_timer_expired(grace_period_s)

        self.reset_alone_timer()
        return False

    async def get_participant_count(self, page: Page) -> int | None:
        """Safely retrieve participant count from the meeting UI.

        Returns the participant count, or None if it could not be determined.
        """
        try:
            return await self._get_participant_count(page)
        except Exception as e:
            logger.warning("Could not read participant count: {}", e)
            return None

    async def disconnect_from_meeting(self, page: Page) -> None:
        return

    @abstractmethod
    async def _get_participant_count(self, page: Page) -> int:
        """Platform-specific implementation to scrape the participant count from the meeting UI.

        Returns the total number of participants currently in the meeting,
        including the bot itself.
        """
        pass
