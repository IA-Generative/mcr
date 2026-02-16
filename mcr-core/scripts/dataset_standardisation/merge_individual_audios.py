"""Audio mixing utility for merging multiple WAV files into a single audio file."""

import os
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Dict, List

import ffmpeg
from loguru import logger

from mcr_meeting.app.configs.base import AudioSettings
from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.setup.logger import log_ffmpeg_command

# Load audio settings
audio_settings = AudioSettings()
sample_rate = audio_settings.SAMPLE_RATE
nb_channels = audio_settings.NB_AUDIO_CHANNELS


def mix_audio_files(audio_paths: List[str]) -> BytesIO:
    """
    Mix multiple WAV audio files into a single mono WAV file.

    All input audio files are mixed together (overlayed/superimposed) rather than
    concatenated. This means all audio plays simultaneously and is combined into
    a single output. The output is normalized to the configured sample rate and
    channel count, with automatic normalization to prevent clipping.

    Args:
        audio_paths (List[str]): List of file paths to WAV files to mix.
            Must contain at least one file path.

    Returns:
        BytesIO: Mixed audio as WAV bytes with configured sample rate and channels.

    Raises:
        ValueError: If audio_paths list is empty.
        InvalidAudioFileError: If mixing fails, files don't exist, or FFmpeg error occurs.

    Example:
        >>> mixed_audio = mix_audio_files(['speaker1.wav', 'speaker2.wav'])
        >>> # Save to file
        >>> with open('output.wav', 'wb') as f:
        ...     f.write(mixed_audio.getvalue())
    """
    if not audio_paths:
        raise ValueError("No audio files provided for mixing")

    # Validate all files exist
    for path in audio_paths:
        if not os.path.exists(path):
            raise InvalidAudioFileError(f"Audio file not found: {path}")

    # Optimization: single file case
    if len(audio_paths) == 1:
        logger.info("Single audio file provided, reading directly without mixing")
        try:
            with open(audio_paths[0], "rb") as f:
                audio_data = f.read()
            return BytesIO(audio_data)
        except Exception as e:
            raise InvalidAudioFileError(
                f"Failed to read audio file {audio_paths[0]}: {e}"
            ) from e

    logger.info(
        "Mixing {} audio files | sr={} ch={}",
        len(audio_paths),
        sample_rate,
        nb_channels,
    )

    try:
        # Create input streams for each audio file
        inputs = [ffmpeg.input(path) for path in audio_paths]

        # Use amix filter to mix all inputs
        # - inputs: number of input streams
        # - duration='longest': output duration is the longest input
        # - normalize=0: prevents clipping by normalizing output amplitude
        mixed = ffmpeg.filter(
            inputs,
            "amix",
            inputs=len(audio_paths),
            duration="longest",
            normalize=0,
        )

        # Configure output stream
        stream = (
            mixed.output(
                "pipe:1",  # Output to stdout
                format="wav",
                ar=sample_rate,  # Audio rate (sample rate)
                ac=nb_channels,  # Audio channels (mono/stereo)
            )
            .overwrite_output()
            .global_args("-loglevel", "warning")
        )

        # Log the FFmpeg command for debugging
        log_ffmpeg_command(stream)

        # Execute FFmpeg command
        output, stderr_output = stream.run(
            capture_stdout=True,
            capture_stderr=True,
        )

        if stderr_output:
            logger.warning(
                "FFmpeg stderr (audio mixing): {}",
                stderr_output.decode(errors="ignore"),
            )

        logger.info("Successfully mixed {} audio files", len(audio_paths))
        return BytesIO(output)

    except ffmpeg.Error as e:
        stderr_text = e.stderr.decode(errors="ignore") if e.stderr else str(e)
        raise InvalidAudioFileError(f"FFmpeg audio mixing failed: {stderr_text}") from e

    except Exception as e:
        raise InvalidAudioFileError(f"Unexpected error during audio mixing: {e}") from e


def group_audio_files_by_prefix(
    directory: Path, prefix_length: int = 4
) -> Dict[str, List[str]]:
    """
    Group WAV audio files by their filename prefix.

    Args:
        directory (Path): Directory containing WAV files to group.
        prefix_length (int): Number of characters to use as group key. Default is 4.

    Returns:
        Dict[str, List[str]]: Dictionary mapping group keys to lists of file paths.
            Files with names shorter than prefix_length are skipped.

    Example:
        >>> groups = group_audio_files_by_prefix(Path("audio/"))
        >>> # {'0001': ['0001_speaker1.wav', '0001_speaker2.wav'], ...}
    """
    groups: Dict[str, List[str]] = defaultdict(list)

    logger.info("Scanning directory: {}", directory)

    if not directory.exists():
        logger.warning("Directory does not exist: {}", directory)
        return groups

    for audio_file in directory.glob("*.wav"):
        filename = audio_file.name
        if len(filename) >= prefix_length:
            group_key = filename[:prefix_length]
            groups[group_key].append(str(audio_file))
            logger.debug("Added {} to group '{}'", filename, group_key)
        else:
            logger.warning(
                "Skipping file '{}' - filename too short (< {} characters)",
                filename,
                prefix_length,
            )

    logger.info(
        "Found {} groups with {} total files",
        len(groups),
        sum(len(v) for v in groups.values()),
    )
    return dict(groups)


def process_audio_group(
    group_key: str, file_paths: List[str], output_directory: Path
) -> bool:
    """
    Mix audio files in a group and save the result.

    Args:
        group_key (str): Identifier for the group (used in output filename).
        file_paths (List[str]): List of audio file paths to mix.
        output_directory (Path): Directory where mixed audio will be saved.

    Returns:
        bool: True if processing succeeded, False otherwise.
    """
    logger.info("Processing group '{}' with {} files", group_key, len(file_paths))

    try:
        # Mix audio files in the group
        mixed_audio = mix_audio_files(file_paths)

        # Create output directory if needed
        output_directory.mkdir(parents=True, exist_ok=True)

        # Save mixed audio
        output_path = output_directory / f"{group_key}_mixed.wav"
        with open(output_path, "wb") as f:
            f.write(mixed_audio.getvalue())

        logger.info("Saved mixed audio to: {}", output_path)
        return True

    except Exception as e:
        logger.error("Failed to process group '{}': {}", group_key, e)
        return False


def main() -> None:
    """
    Group audio files by their first 4 characters and mix each group.

    Reads WAV files from individual_audios_path, groups them by the first 4
    characters of their filename, mixes each group, and saves the results
    to raw_audios_path.
    """
    # Define paths - TODO: Update these paths
    individual_audios_path = Path(
        "mcr_meeting/evaluation/data/clean_dataset/individual_audios"
    )
    raw_audios_path = Path("mcr_meeting/evaluation/data/clean_dataset/raw_audios")

    logger.info("Starting audio mixing process")
    logger.info("Input directory: {}", individual_audios_path)
    logger.info("Output directory: {}", raw_audios_path)

    # Group files by first 4 characters
    groups = group_audio_files_by_prefix(individual_audios_path, prefix_length=4)

    if not groups:
        logger.warning("No audio groups found. Exiting.")
        return

    # Process each group
    success_count = 0
    failure_count = 0

    for group_key, file_paths in groups.items():
        if process_audio_group(group_key, file_paths, raw_audios_path):
            success_count += 1
        else:
            failure_count += 1

    logger.info(
        "Audio mixing completed: {} groups succeeded, {} groups failed",
        success_count,
        failure_count,
    )


if __name__ == "__main__":
    main()
