"""Single Playwright bot that joins a Visio meeting and streams a WAV file.

The bot joins as a guest (no auth), un-mutes itself, and lets Chromium emit
the WAV file via ``--use-file-for-fake-audio-capture``. No recording happens.
"""

import asyncio

from loguru import logger
from playwright.async_api import async_playwright

from config import BenchmarkConfig, BotTask

WAITING_ROOM_TIMEOUT_MS = 300_000
DEFAULT_ACTION_TIMEOUT_MS = 60_000

# mirror of VisioStrategy — keep in sync
# Source: mcr-capture-worker/mcr_capture_worker/services/connection_strategies/visio_connection.py
NAME_INPUT_SELECTOR = 'input[autocomplete="name"]'
DISABLE_CAMERA_BUTTON_NAME = "Disable camera"
JOIN_BUTTON_NAME = "Join"
IN_MEETING_SELECTOR = ".lk-video-conference"


def _build_chromium_args(audio_abs_path: str) -> list[str]:
    # Mirrors meeting_audio_recorder.py launch args, plus the file-injection flag.
    # --lang=en-US pins the Visio UI language so the button-name selectors match.
    return [
        "--no-sandbox",
        "--use-fake-device-for-media-stream",
        "--use-fake-ui-for-media-stream",
        "--autoplay-policy=no-user-gesture-required",
        "--disable-dev-shm-usage",
        "--lang=en-US",
        f"--use-file-for-fake-audio-capture={audio_abs_path}%noloop",
    ]


async def run_bot(
    task: BotTask,
    bot_name: str,
    duration_s: float,
    cfg: BenchmarkConfig,
) -> None:
    audio_abs = str(task.audio.resolve())
    logger.info("[{}] launching Chromium (headless={}), audio={}", bot_name, cfg.headless, audio_abs)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=cfg.headless,
            args=_build_chromium_args(audio_abs),
        )
        try:
            context = await browser.new_context(
                permissions=["microphone", "camera"],
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = await context.new_page()
            page.set_default_timeout(DEFAULT_ACTION_TIMEOUT_MS)

            logger.info("[{}] joining {}", bot_name, task.url)
            await page.goto(task.url)
            await page.locator(NAME_INPUT_SELECTOR).fill(bot_name)
            await page.get_by_role("button", name=DISABLE_CAMERA_BUTTON_NAME).click()
            # Mic stays ON so Chromium streams the file to the meeting.
            await page.get_by_role("button", name=JOIN_BUTTON_NAME).click()
            await page.wait_for_selector(
                IN_MEETING_SELECTOR, state="visible", timeout=WAITING_ROOM_TIMEOUT_MS
            )

            total_sleep = duration_s + cfg.post_stream_buffer_s
            logger.info("[{}] joined, streaming for ~{:.1f}s", bot_name, duration_s)
            await asyncio.sleep(total_sleep)
            logger.info("[{}] done", bot_name)
        finally:
            await browser.close()
