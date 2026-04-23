import time
from abc import ABC, abstractmethod
from io import BytesIO

from loguru import logger

from mcr_capture_worker.settings.settings import CaptureSettings

capture_settings = CaptureSettings()


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

    async def should_disconnect(self, grace_period_s: int) -> bool:
        """Check participant count and return True if the bot should auto-disconnect."""
        participant_count = await self.get_participant_count()

        if participant_count is None or participant_count <= 1:
            self.start_alone_timer()
            return self.is_alone_timer_expired(grace_period_s)

        self.reset_alone_timer()
        return False

    async def get_participant_count(self) -> int | None:
        """Safely retrieve participant count.

        Returns the participant count, or None if it could not be determined.
        """
        try:
            return await self._get_participant_count()
        except Exception as e:
            logger.warning("Could not read participant count: {}", e)
            return None

    async def enforce_bot_muted(self) -> None:
        return

    async def disconnect_from_meeting(self) -> None:
        return

    async def enable_chunk_size_based_disconnection(self, data: BytesIO) -> None:
        data_size = len(data.getvalue()) / capture_settings.BYTES_PER_KB

        if (
            self._alone_since is None
            and data_size <= capture_settings.EMPTY_CHUNK_THRESHOLD
        ):
            self.start_alone_timer()
        elif (
            self._alone_since is not None
            and data_size > capture_settings.EMPTY_CHUNK_THRESHOLD
        ):
            self.reset_alone_timer()

    @abstractmethod
    async def _get_participant_count(self) -> int:
        """Platform-specific implementation of participant count retrieval.

        Returns the total number of participants currently in the meeting,
        including the bot itself.
        """
        pass
