import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

from loguru import logger

from mcr_capture_worker.clients.meeting_transition_client import MeetingApiClient
from mcr_capture_worker.models.meeting_model import Meeting
from mcr_capture_worker.services.meeting_monitors.webex_node_monitor import (
    WebexNodeMeetingMonitor,
)
from mcr_capture_worker.services.webex_node_transport import (
    WebexCommand,
    WebexEvent,
    WebexNodeTransport,
)

PollStarter = Callable[[Callable[[], Awaitable[None]]], Awaitable[None]]


class WebexNodeCapture:
    """Full Webex Node subprocess capture session.

    Owns transport, monitor, event dispatch, and task lifecycle. The recorder
    provides a chunk handler and a poll function; everything else is internal.
    """

    def __init__(
        self,
        meeting: Meeting,
        meeting_transition_client: MeetingApiClient,
        script_path: Path,
        *,
        on_chunk: Callable[[bytes], None],
        on_connected: Callable[[], None] | None = None,
    ) -> None:
        if meeting.url is None:
            raise ValueError("Webex meeting doesn't have a valid url")

        self._meeting = meeting
        self._transition_client = meeting_transition_client
        self._on_chunk_callback = on_chunk
        self._on_connected = on_connected
        self._monitor = WebexNodeMeetingMonitor()
        self._recording_started = asyncio.Event()
        self._transport = WebexNodeTransport(
            script_path=script_path,
            meeting_url=meeting.url,
            bot_name=f"FCR Agent de {meeting.owner.email}",
            on_event=self._on_event,
            on_chunk=self._on_chunk,
        )

    @property
    def monitor(self) -> WebexNodeMeetingMonitor:
        return self._monitor

    async def run(self, poll_fn: PollStarter) -> None:
        """Run the capture until transport terminates or poll_fn triggers stop.

        poll_fn is called with a stop callback; it should poll DB/auto-disconnect
        conditions and invoke the callback when stop is warranted.
        """
        transport_task = asyncio.create_task(self._transport.run())
        poll_task = asyncio.create_task(self._poll_after_recording_started(poll_fn))
        try:
            _, pending = await asyncio.wait(
                {transport_task, poll_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            if transport_task.done() and not transport_task.cancelled():
                transport_task.result()
        except Exception:
            transport_task.cancel()
            poll_task.cancel()
            raise

    async def _poll_after_recording_started(self, poll_fn: PollStarter) -> None:
        # Wait for the bot to actually be recording before polling for stop
        # conditions. Otherwise the poll loop races against subprocess startup
        # and sees status != CAPTURE_IN_PROGRESS immediately.
        await self._recording_started.wait()
        await poll_fn(self._send_stop)

    async def _send_stop(self) -> None:
        await self._transport.send_command(WebexCommand.STOP)

    async def _on_event(self, event: WebexEvent, data: dict[str, Any]) -> None:
        match event:
            case WebexEvent.JOINED:
                if self._on_connected is not None:
                    self._on_connected()
                await self._transition_client.start_capture_bot(self._meeting.id)
            case WebexEvent.PARTICIPANTS:
                self._monitor.update_participant_count(data.get("count", 0))
            case WebexEvent.RECORDING_STARTED:
                logger.info("WEBEX NODE: recording started")
                self._recording_started.set()
            case WebexEvent.RECORDING_STOPPED:
                logger.info("WEBEX NODE: recording stopped")
            case WebexEvent.ERROR:
                logger.error("WEBEX NODE: error: {}", data.get("message", "unknown"))

    async def _on_chunk(self, payload: bytes) -> None:
        self._on_chunk_callback(payload)
