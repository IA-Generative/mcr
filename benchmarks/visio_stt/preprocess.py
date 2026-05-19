"""Convert arbitrary audio files to WAV 16 kHz mono 16-bit PCM via ffmpeg.

The Chromium flag ``--use-file-for-fake-audio-capture`` only accepts WAV files
in this exact format. Silent fallback would produce silence on the wire, so
we validate the output strictly.
"""

import argparse
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from loguru import logger

TARGET_CHANNELS = 1
TARGET_SAMPLE_RATE_HZ = 16000
TARGET_SAMPLE_WIDTH_BYTES = 2


def convert_to_wav(src: Path, dst: Path) -> None:
    """Convert any audio file to WAV 16 kHz mono 16-bit PCM via ffmpeg."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-ac",
        str(TARGET_CHANNELS),
        "-ar",
        str(TARGET_SAMPLE_RATE_HZ),
        "-sample_fmt",
        "s16",
        str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def validate_wav(path: Path) -> float:
    """Assert the WAV matches Chromium's fake-audio-capture expectations.

    Returns the duration in seconds. Raises ValueError on any mismatch.
    """
    with wave.open(str(path), "rb") as w:
        channels = w.getnchannels()
        framerate = w.getframerate()
        sampwidth = w.getsampwidth()
        nframes = w.getnframes()

    if channels != TARGET_CHANNELS:
        raise ValueError(f"{path}: expected {TARGET_CHANNELS} channel(s), got {channels}")
    if framerate != TARGET_SAMPLE_RATE_HZ:
        raise ValueError(
            f"{path}: expected {TARGET_SAMPLE_RATE_HZ} Hz, got {framerate}"
        )
    if sampwidth != TARGET_SAMPLE_WIDTH_BYTES:
        raise ValueError(
            f"{path}: expected {TARGET_SAMPLE_WIDTH_BYTES}-byte samples, got {sampwidth}"
        )

    return nframes / framerate


def _iter_source_files(src_dir: Path) -> list[Path]:
    return sorted(p for p in src_dir.iterdir() if p.is_file() and not p.name.startswith("."))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert audio files to WAV 16 kHz mono 16-bit PCM."
    )
    parser.add_argument("src_dir", type=Path, help="Directory containing input audio files.")
    parser.add_argument("dst_dir", type=Path, help="Directory where converted WAVs are written.")
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        logger.error("ffmpeg not found in PATH. Install it first (e.g. `brew install ffmpeg`).")
        return 1

    src_dir: Path = args.src_dir
    dst_dir: Path = args.dst_dir

    if not src_dir.is_dir():
        logger.error("Source directory does not exist: {}", src_dir)
        return 1

    dst_dir.mkdir(parents=True, exist_ok=True)
    sources = _iter_source_files(src_dir)
    if not sources:
        logger.warning("No files found in {}", src_dir)
        return 0

    failures = 0
    for src in sources:
        dst = dst_dir / f"{src.stem}.wav"
        logger.info("Converting {} -> {}", src.name, dst.name)
        try:
            convert_to_wav(src, dst)
            duration = validate_wav(dst)
            logger.info("  OK {:.2f}s", duration)
        except (subprocess.CalledProcessError, ValueError) as exc:
            logger.error("  FAILED: {}", exc)
            failures += 1

    if failures:
        logger.error("{} / {} files failed", failures, len(sources))
        return 1
    logger.info("{} file(s) converted successfully", len(sources))
    return 0


if __name__ == "__main__":
    sys.exit(main())
