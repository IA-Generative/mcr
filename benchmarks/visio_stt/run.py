"""Orchestrator: launch N bots in parallel to benchmark Visio native STT.

Paths in the config JSON are resolved relative to the current working directory.
Run this script from the ``benchmarks/visio_stt/`` folder.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from bot import run_bot
from config import BenchmarkConfig, BotTask, load_config
from preprocess import validate_wav


def _preflight(tasks: list[BotTask]) -> dict[int, float]:
    """Validate every WAV before touching Playwright. Returns {index: duration_s}."""
    durations: dict[int, float] = {}
    for i, task in enumerate(tasks):
        duration = validate_wav(task.audio)
        durations[i] = duration
        logger.info("Task #{}: {} -> {:.2f}s @ {}", i, task.audio, duration, task.url)
    return durations


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Visio STT benchmark.")
    parser.add_argument("--config", type=Path, required=True, help="Path to the JSON config.")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate config and audio files, then exit without launching browsers.",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run Chromium with a visible window (overrides config).",
    )
    args = parser.parse_args()

    try:
        cfg: BenchmarkConfig = load_config(args.config)
    except (FileNotFoundError, ValidationError) as exc:
        logger.error("Invalid config: {}", exc)
        return 1

    if args.no_headless:
        cfg = cfg.model_copy(update={"headless": False})

    try:
        durations = _preflight(cfg.tasks)
    except ValueError as exc:
        logger.error("Pre-flight WAV validation failed: {}", exc)
        return 1

    if args.validate_only:
        logger.info("--validate-only: {} task(s) ready, exiting without launching bots.",
                    len(cfg.tasks))
        return 0

    return asyncio.run(_run_all(cfg, durations))


async def _run_all(cfg: BenchmarkConfig, durations: dict[int, float]) -> int:
    coros = [
        run_bot(task, f"STT-Bench-{i + 1:02d}", durations[i], cfg)
        for i, task in enumerate(cfg.tasks)
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)

    failures = 0
    for i, result in enumerate(results):
        bot_name = f"STT-Bench-{i + 1:02d}"
        if isinstance(result, BaseException):
            failures += 1
            logger.opt(exception=result).error("[{}] failed", bot_name)
        else:
            logger.info("[{}] success", bot_name)

    total = len(results)
    if failures:
        logger.error("Run finished: {}/{} bots failed", failures, total)
        return 1
    logger.info("Run finished: {}/{} bots succeeded", total, total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
