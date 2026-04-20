import asyncio
import json
import struct
from collections.abc import Awaitable, Callable
from contextlib import suppress
from enum import StrEnum
from pathlib import Path
from typing import Any

from loguru import logger


class WebexCommand(StrEnum):
    """Commands the parent writes on the subprocess stdin."""

    STOP = "stop"


class WebexEvent(StrEnum):
    """Events the subprocess emits as 'E' frames on stdout.

    Must stay in sync with sendEvent({ event: ... }) calls in webex_node_bot.js.
    """

    JOINED = "joined"
    PARTICIPANTS = "participants"
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    ERROR = "error"


TERMINAL_EVENTS = frozenset({WebexEvent.RECORDING_STOPPED, WebexEvent.ERROR})


class WebexNodeTransport:
    """Transport layer for the Webex Node subprocess.

    Owns subprocess lifecycle, binary frame protocol (1-byte tag + 4-byte BE length
    + payload), and stderr logging. Delivers parsed events and raw audio chunks
    via callbacks.
    """

    def __init__(
        self,
        script_path: Path,
        meeting_url: str,
        bot_name: str,
        *,
        on_event: Callable[[WebexEvent, dict[str, Any]], Awaitable[None]],
        on_chunk: Callable[[bytes], Awaitable[None]],
    ) -> None:
        self._script_path = script_path
        self._meeting_url = meeting_url
        self._bot_name = bot_name
        self._on_event = on_event
        self._on_chunk = on_chunk
        self._proc: asyncio.subprocess.Process | None = None
        self._stderr_task: asyncio.Task[None] | None = None

    async def run(self) -> None:
        """Spawn the subprocess, read frames until done, then clean up."""
        self._proc = await self._spawn()
        logger.info("WEBEX NODE: started subprocess pid={}", self._proc.pid)
        self._stderr_task = asyncio.create_task(self._log_stderr())
        try:
            await self._read_loop()
        finally:
            await self._cleanup()

    async def send_command(self, cmd: WebexCommand) -> None:
        """Write a line-delimited command to the subprocess stdin.

        Safe to call if the process has already exited.
        """
        if (
            self._proc is None
            or self._proc.stdin is None
            or self._proc.returncode is not None
        ):
            logger.warning(
                "WEBEX NODE: cannot send '{}', process not running", cmd.value
            )
            return
        try:
            self._proc.stdin.write(f"{cmd.value}\n".encode())
            await self._proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            logger.warning("WEBEX NODE: pipe broken sending '{}'", cmd.value)

    async def _spawn(self) -> asyncio.subprocess.Process:
        return await asyncio.create_subprocess_exec(
            "node",
            str(self._script_path),
            self._meeting_url,
            self._bot_name,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def _read_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        try:
            while True:
                header = await self._proc.stdout.readexactly(5)
                tag = chr(header[0])
                (length,) = struct.unpack(">I", header[1:5])
                payload = await self._proc.stdout.readexactly(length)

                if tag == "E":
                    msg = json.loads(payload)
                    raw_name = msg.get("event", "")
                    try:
                        event = WebexEvent(raw_name)
                    except ValueError:
                        logger.warning("WEBEX NODE: unknown event {!r}", raw_name)
                        continue
                    await self._on_event(event, msg)
                    if event in TERMINAL_EVENTS:
                        return
                elif tag == "C":
                    await self._on_chunk(payload)
        except asyncio.IncompleteReadError:
            logger.error("WEBEX NODE: subprocess closed stdout unexpectedly")

    async def _log_stderr(self) -> None:
        assert self._proc is not None and self._proc.stderr is not None
        async for raw_line in self._proc.stderr:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if line:
                logger.info("WEBEX NODE: {}", line)

    async def _cleanup(self) -> None:
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._stderr_task

        if self._proc is not None and self._proc.returncode is None:
            self._proc.terminate()
            await self._proc.wait()
