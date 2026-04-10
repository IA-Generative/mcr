from asyncio import sleep

from loguru import logger
from playwright.async_api import Frame, FrameLocator, Page

from mcr_capture_worker.models.meeting_model import Meeting
from mcr_capture_worker.schemas.meeting_schema import is_meeting_with_url
from mcr_capture_worker.services.connection_strategies.abstract_connection import (
    ConnectionStrategy,
)

INJECT_STREAM_SCRIPTS = [
    "mcr_capture_worker/services/audio/inject_stream_strategy/config.js",
    "mcr_capture_worker/services/audio/inject_stream_strategy/streamUtils.js",
    "mcr_capture_worker/services/audio/inject_stream_strategy/recorderController.js",
    "mcr_capture_worker/services/audio/inject_stream_strategy/index.js",
]


class WebexStrategy(ConnectionStrategy):
    MEETING_IFRAME_ID = "#unified-webclient-iframe"
    CONNECTION_TIMEOUT = 30000  # 30s
    BOT_NAME_INPUT_SELECTOR = "input[autocomplete='name']"
    CAMERA_BUTTON_SELECTOR = "[data-test='camera-button']"
    JOIN_BUTTON_ID = "#join-button"
    SELECT_BROWSER_BUTTON_LABEL = "Join from this browser"

    def _get_meeting_frame(self, page: Page) -> FrameLocator:
        return page.frame_locator(self.MEETING_IFRAME_ID)

    async def connect_to_meeting(self, page: Page, meeting: Meeting) -> None:
        if not is_meeting_with_url(meeting):
            raise ValueError("Webex meeting doesn't have a valid url")

        await page.goto(meeting.url, wait_until="domcontentloaded")
        await self._optionally_select_webex_browser_version(page)

    async def set_bot_name(self, page: Page, meeting: Meeting) -> None:
        frame = self._get_meeting_frame(page)
        await self._dismiss_media_permissions_dialog(frame)
        locator = frame.locator(self.BOT_NAME_INPUT_SELECTOR)
        await locator.wait_for(state="visible", timeout=self.CONNECTION_TIMEOUT)
        await locator.fill(self.get_agent_name(meeting))

    async def join_waiting_room_and_set_devices(self, page: Page) -> None:
        await self._optionally_disable_camera(page)
        await self._join_waiting_room(page)

    async def wait_for_webRTC_connection(self, page: Page) -> None:
        logger.info(
            "WEBEX: Skipping MediaStream check (will be available when participants speak)"
        )

    async def load_recording_script(self, page: Page) -> None:
        # Main page: receiver that accepts audio tracks from iframe loopback
        await page.add_init_script(
            path="mcr_capture_worker/services/audio/inject_stream_strategy/webrtcMainReceiver.js"
        )
        # All frames (including iframe): bridge that intercepts RTCPeerConnection
        await page.context.add_init_script(
            path="mcr_capture_worker/services/audio/inject_stream_strategy/webrtcBridge.js"
        )

    def _get_iframe_frame(self, page: Page) -> Frame:
        for frame in page.frames:
            if frame.name == "unified-webclient-iframe":
                return frame
        raise RuntimeError("Could not find Webex meeting iframe")

    async def post_connect_setup(self, page: Page) -> None:
        iframe = self._get_iframe_frame(page)

        loopback_result = await iframe.evaluate("window.__startBridgeLoopback()")
        logger.info("WEBEX bridge loopback result: {}", loopback_result)

        await sleep(5)

        for script_path in INJECT_STREAM_SCRIPTS:
            with open(script_path) as f:
                await page.evaluate(f.read())

    async def _join_waiting_room(self, page: Page) -> None:
        frame = self._get_meeting_frame(page)
        locator = frame.locator(self.JOIN_BUTTON_ID)
        await locator.wait_for(state="visible", timeout=self.CONNECTION_TIMEOUT)
        await locator.click()
        await sleep(10)

    async def _dismiss_media_permissions_dialog(self, frame: FrameLocator) -> None:
        """Dismiss the 'Do you want people to hear and see you?' dialog."""
        for _ in range(3):
            try:
                btn = frame.get_by_role(
                    "button", name="Continue without microphone and camera"
                )
                await btn.wait_for(state="visible", timeout=5000)
                await btn.click()
                logger.info("Dismissed media permissions dialog")
            except Exception:
                try:
                    btn = frame.get_by_role(
                        "button", name="Continue without microphone"
                    )
                    await btn.wait_for(state="visible", timeout=3000)
                    await btn.click()
                    logger.info("Dismissed microphone permissions dialog")
                except Exception:
                    break

    async def _optionally_disable_camera(self, page: Page) -> None:
        try:
            frame = self._get_meeting_frame(page)
            locator = frame.locator(self.CAMERA_BUTTON_SELECTOR)
            await locator.wait_for(state="visible", timeout=5000)
            await locator.click()
        except Exception:
            pass

    async def _optionally_select_webex_browser_version(self, page: Page) -> None:
        # Dismiss cookie consent if present
        try:
            accept_btn = page.get_by_role("button", name="Accept")
            await accept_btn.wait_for(state="visible", timeout=5000)
            await accept_btn.click()
            logger.info("Accepted cookie consent")
        except Exception:
            pass

        try:
            locator = page.get_by_role("button", name=self.SELECT_BROWSER_BUTTON_LABEL)
            await locator.wait_for(state="visible", timeout=20000)
            await locator.click()
        except Exception:
            pass

        # Handle "Let's make sure you're on time" interstitial dialog
        try:
            fallback_btn = page.locator("#fallBkJoinByBrowser")
            await fallback_btn.wait_for(state="visible", timeout=5000)
            await fallback_btn.click()
            logger.info("Dismissed 'join from browser' interstitial dialog")
        except Exception:
            pass
