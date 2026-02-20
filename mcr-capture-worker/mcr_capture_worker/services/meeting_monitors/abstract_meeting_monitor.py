from abc import ABC, abstractmethod
from typing import Optional

from loguru import logger
from playwright.async_api import Page


class MeetingMonitor(ABC):
    @abstractmethod
    async def _get_participant_count(self, page: Page) -> int:
        """Platform-specific implementation to scrape the participant count from the meeting UI.

        Returns the total number of participants currently in the meeting,
        including the bot itself.
        """
        pass

    async def get_participant_count(self, page: Page) -> Optional[int]:
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
