import asyncio
from typing import Any, Coroutine

from loguru import logger


class UploadQueue:
    def __init__(self) -> None:
        self.pending_uploads: list[asyncio.Task[Any]] = []

    def append(self, coroutine: Coroutine[Any, Any, Any]) -> None:
        task = asyncio.create_task(coroutine)
        task.add_done_callback(self.cleanup_task_on_finished)
        self.pending_uploads.append(task)

    def cleanup_task_on_finished(self, task: asyncio.Task[Any]) -> None:
        """Remove finished task from pending_uploads."""
        try:
            self.pending_uploads.remove(task)
        except ValueError:
            pass  # already removed
        if task.exception():
            # log or handle upload failure
            logger.error("Task failed: {}", task.exception())

    async def wait_for_all_to_finish(self) -> None:
        try:
            await asyncio.gather(*self.pending_uploads)
        except Exception as e:
            logger.error("Error in wait_for_all_to_finish: {}", e)
