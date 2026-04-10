import json
import os
import re
import tempfile
from collections.abc import Iterator
from io import BytesIO

import ffmpeg
import numpy as np
import numpy.typing as npt
from loguru import logger

from mcr_meeting.app.configs.base import (
    AudioSettings,
    NoiseDetectionSettings,
    NormalizedAudioVolumeSettings,
    Speech2TextSettings,
)
from mcr_meeting.app.exceptions.exceptions import (
    InvalidAudioFileError,
    NoAudioFoundError,
    SilentAudioError,
)
from mcr_meeting.app.schemas.S3_types import S3Object
from mcr_meeting.app.services.s3_service import get_file_from_s3
from mcr_meeting.setup.logger import log_ffmpeg_command

s2t_settings = Speech2TextSettings()
audio_settings = AudioSettings()
noise_detection_settings = NoiseDetectionSettings()
normalized_audio_volume_settings = NormalizedAudioVolumeSettings()
sample_rate = audio_settings.SAMPLE_RATE
nb_channels = audio_settings.NB_AUDIO_CHANNELS


def _get_audio_duration_seconds(wav_bytes: BytesIO) -> float:
    """Compute duration of normalized WAV audio from byte size.

    Works because we control the WAV output format (header size, bytes per sample,
    sample rate, and channel count are all defined in AudioSettings).
    """
    byte_count = len(wav_bytes.getvalue()) - audio_settings.WAV_HEADER_SIZE
    return byte_count / (sample_rate * nb_channels * audio_settings.BYTES_PER_SAMPLE)


def _detect_silences_absolute(
    wav_bytes: BytesIO,
) -> list[tuple[float, float]]:
    """Detect silence segments using a fixed absolute dB threshold.

    Unlike _detect_silences (which is relative to mean volume), this uses a fixed
    noise floor so it reliably detects silence even on fully silent audio where the
    mean volume is already at the floor.
    """
    threshold_db = noise_detection_settings.SILENT_AUDIO_NOISE_FLOOR_DB

    af = f"silencedetect=noise={threshold_db}dB:d={noise_detection_settings.MIN_SILENCE_DURATION}"
    _, stderr = (
        ffmpeg.input("pipe:0", format="wav")
        .output("pipe:", format="null", af=af)
        .run(input=wav_bytes.getvalue(), capture_stdout=True, capture_stderr=True)
    )
    return _parse_silence_intervals(stderr.decode("utf-8", errors="replace"))


def compute_silence_ratio(wav_bytes: BytesIO) -> float:
    """Compute the ratio of silence duration to total audio duration.

    Uses ffmpeg silencedetect with a fixed absolute threshold to identify silent
    intervals, then returns the proportion of the audio that is silent.

    Args:
        wav_bytes: Normalized WAV audio bytes.

    Returns:
        Float between 0.0 (no silence) and 1.0 (fully silent).
    """
    total_duration = _get_audio_duration_seconds(wav_bytes)
    if total_duration <= 0:
        return 1.0

    silences = _detect_silences_absolute(wav_bytes)
    silence_duration = sum(end - start for start, end in silences)
    wav_bytes.seek(0)
    return min(silence_duration / total_duration, 1.0)


def check_audio_is_not_silent(wav_bytes: BytesIO, meeting_id: int) -> None:
    """Check that the audio is not silent, raise SilentAudioError otherwise.

    Args:
        wav_bytes: Normalized WAV audio bytes.
        meeting_id: ID of the meeting (included in the error message).

    Raises:
        SilentAudioError: If the silence ratio exceeds the configured threshold.
    """
    silence_ratio = compute_silence_ratio(wav_bytes)
    if silence_ratio >= noise_detection_settings.SILENT_AUDIO_THRESHOLD:
        raise SilentAudioError(
            f"Silent audio detected for meeting {meeting_id}: "
            f"audio is {silence_ratio:.0%} silent "
            f"(threshold: {noise_detection_settings.SILENT_AUDIO_THRESHOLD:.0%})"
        )


def audio_bytes_to_wav_bytes(input_bytes: BytesIO) -> BytesIO:
    """
    Bytes→normalized WAV bytes, using FFmpeg via stdin/stdout pipes.

    Args:
        input_bytes (BytesIO): Raw audio bytes to be normalized.
    Returns:
        BytesIO: Normalized WAV bytes.
    """

    logger.info(
        "Normalizing audio (bytes→bytes) | sr={} ch={}",
        sample_rate,
        nb_channels,
    )

    # Use a temporary file for input because FFmpeg cannot seek on stdin
    # This is critical for formats like m4a/mp4 where metadata might be at the end
    with tempfile.NamedTemporaryFile(delete=False) as tmp_input:
        tmp_input.write(input_bytes.getvalue())
        tmp_input_path = tmp_input.name

    try:
        # pipe:1 = write to stdout
        stream = ffmpeg.input(tmp_input_path, err_detect="ignore_err")
        stream = (
            stream.output(
                "pipe:1",
                format="wav",  # Specify WAV container format
                ar=sample_rate,  # Audio rate (sample rate)
                ac=nb_channels,  # Audio channels (mono/stereo)
            )
            .overwrite_output()
            .global_args("-loglevel", "warning")
        )

        log_ffmpeg_command(stream)

        output, stderr_output = stream.run(
            capture_stdout=True,
            capture_stderr=True,
        )
        if stderr_output:
            logger.warning(
                "FFmpeg stderr (bytes→bytes): {}", stderr_output.decode(errors="ignore")
            )
        return BytesIO(output)

    except ffmpeg.Error as e:
        stderr_text = e.stderr.decode(errors="ignore") if e.stderr else str(e)
        raise InvalidAudioFileError(
            f"FFmpeg normalization failed: {stderr_text}"
        ) from e
    except Exception as e:
        raise InvalidAudioFileError(
            f"Unexpected error during normalization: {e}"
        ) from e
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_input_path):
            os.remove(tmp_input_path)


def filter_noise_from_audio_bytes(input_bytes: BytesIO) -> BytesIO:
    """
    Apply noise reduction and audio enhancement filters to audio bytes.

    Applies FFmpeg audio filters based on the provided filter string.

    Args:
        input_bytes (BytesIO): Raw audio bytes to be filtered.
        filters (str): FFmpeg audio filter string to apply.
    Returns:
        BytesIO: Filtered audio bytes.
    """
    s2t_settings = Speech2TextSettings()
    filters = s2t_settings.NOISE_FILTERS

    logger.info("Applying noise reduction filters: {}", filters)

    # Input is already normalized WAV, specify format explicitly
    stream = ffmpeg.input("pipe:0", format="wav", err_detect="ignore_err")

    try:
        # Apply audio filters - maintain WAV format with correct sample rate and channels
        stream = stream.output(
            "pipe:1",
            format="wav",
            ar=sample_rate,  # Maintain audio sample rate
            ac=nb_channels,  # Maintain audio channels
            af=filters,  # Audio filter string
        )

        stream = stream.overwrite_output().global_args("-loglevel", "warning")
        log_ffmpeg_command(stream)

        output, stderr_output = stream.run(
            input=input_bytes.getvalue(),
            capture_stdout=True,
            capture_stderr=True,
        )
        if stderr_output:
            logger.warning(
                "FFmpeg stderr (noise filtering): {}",
                stderr_output.decode(errors="ignore"),
            )
        return BytesIO(output)
    except ffmpeg.Error as e:
        stderr_text = e.stderr.decode(errors="ignore") if e.stderr else str(e)
        raise InvalidAudioFileError(
            f"FFmpeg noise filtering failed: {stderr_text}"
        ) from e
    except Exception as e:
        raise InvalidAudioFileError(
            f"Unexpected error during noise filtering: {e}"
        ) from e


def download_and_concatenate_s3_audio_chunks_into_bytes(
    obj_iterator: Iterator[S3Object],
) -> BytesIO:
    """
    Concatenates audio chunks from an S3 object iterator into a BytesIO object.

    Args:
        obj_iterator (Iterator[S3Object]): An iterator over S3 objects containing audio chunks.

    Returns:
        BytesIO: A BytesIO object containing the concatenated audio data.

    Raises:
        NoAudioFoundError: If no audio chunks are found
        InvalidAudioFileError: If S3 download fails
    """
    audio_buffer = BytesIO()
    chunk_count = 0

    for obj_info in obj_iterator:
        chunk_count += 1
        try:
            audio_chunk_data = get_file_from_s3(object_name=obj_info.object_name)
            audio_buffer.write(audio_chunk_data.read())
        except Exception as chunk_error:
            raise InvalidAudioFileError(
                f"Failed to download audio chunk {obj_info.object_name}: {chunk_error}"
            ) from chunk_error

    if chunk_count == 0:
        raise NoAudioFoundError("No audio chunks found in iterator")

    audio_buffer.seek(0)
    return audio_buffer


def _parse_mean_volume(ffmpeg_stderr: str) -> float:
    """Parse mean_volume in dBFS from ffmpeg volumedetect stderr output."""
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", ffmpeg_stderr)
    if not match:
        raise RuntimeError(
            f"Could not parse mean_volume from ffmpeg output.\n\n{ffmpeg_stderr}"
        )
    return float(match.group(1))


def _parse_silence_intervals(
    ffmpeg_stderr: str,
) -> list[tuple[float, float]]:
    """Parse silence intervals from ffmpeg silencedetect stderr output."""
    starts = [
        float(x)
        for x in re.findall(r"silence_start:\s*([0-9]+(?:\.[0-9]+)?)", ffmpeg_stderr)
    ]
    ends = [
        float(x)
        for x in re.findall(r"silence_end:\s*([0-9]+(?:\.[0-9]+)?)", ffmpeg_stderr)
    ]
    return list(zip(starts, ends))


def _parse_loudnorm_stats(ffmpeg_stderr: str) -> dict[str, str]:
    """Parse loudnorm statistics (JSON) from ffmpeg stderr output (pass 1)."""
    json_start = ffmpeg_stderr.rfind("{")
    json_end = ffmpeg_stderr.rfind("}") + 1
    if json_start == -1 or json_end == 0:
        raise RuntimeError(
            f"Could not parse loudnorm stats from ffmpeg output.\n\n{ffmpeg_stderr}"
        )
    result: dict[str, str] = json.loads(ffmpeg_stderr[json_start:json_end])
    return result


def _get_mean_volume_db(wav_bytes: BytesIO) -> float:
    """Return the mean_volume in dBFS via ffmpeg volumedetect."""
    _, stderr = (
        ffmpeg.input("pipe:0", format="wav")
        .output("pipe:", format="null", af="volumedetect")
        .run(input=wav_bytes.getvalue(), capture_stdout=True, capture_stderr=True)
    )
    return _parse_mean_volume(stderr.decode("utf-8", errors="replace"))


def _detect_silences(
    wav_bytes: BytesIO,
) -> list[tuple[float, float]]:
    """Detect silence segments using a relative threshold (mean_volume - offset dB)."""
    mean_volume_db = _get_mean_volume_db(wav_bytes)
    threshold_db = mean_volume_db - noise_detection_settings.SILENCE_THRESHOLD_OFFSET_DB

    af = f"silencedetect=noise={threshold_db}dB:d={noise_detection_settings.MIN_SILENCE_DURATION}"
    _, stderr = (
        ffmpeg.input("pipe:0", format="wav")
        .output("pipe:", format="null", af=af)
        .run(input=wav_bytes.getvalue(), capture_stdout=True, capture_stderr=True)
    )
    return _parse_silence_intervals(stderr.decode("utf-8", errors="replace"))


def two_pass_volume_normalization(wav_bytes: BytesIO) -> BytesIO:
    """Normalize volume using two-pass EBU R128 loudnorm."""
    loudnorm_base = f"loudnorm=I={normalized_audio_volume_settings.TARGET_LUFS}:TP={normalized_audio_volume_settings.TRUE_PEAK}:LRA={normalized_audio_volume_settings.LOUDNESS_RANGE}"

    # Pass 1: measure loudness statistics
    _, stderr = (
        ffmpeg.input("pipe:0", format="wav")
        .output("pipe:", format="null", af=f"{loudnorm_base}:print_format=json")
        .run(input=wav_bytes.getvalue(), capture_stdout=True, capture_stderr=True)
    )
    stats = _parse_loudnorm_stats(stderr.decode("utf-8", errors="replace"))

    # Pass 2: apply normalization with measured values
    out, _ = (
        ffmpeg.input("pipe:0", format="wav")
        .output(
            "pipe:",
            format="wav",
            ar=audio_settings.SAMPLE_RATE,
            af=(
                f"{loudnorm_base}:"
                f"measured_I={stats['input_i']}:"
                f"measured_TP={stats['input_tp']}:"
                f"measured_LRA={stats['input_lra']}:"
                f"measured_thresh={stats['input_thresh']}:"
                f"offset={stats['target_offset']}:"
                f"linear=true"
            ),
        )
        .run(input=wav_bytes.getvalue(), capture_stdout=True, capture_stderr=True)
    )
    return BytesIO(out)


def _read_audio_samples(
    wav_bytes: BytesIO,
) -> npt.NDArray[np.float32]:
    """Read WAV bytes into float32 mono samples via ffmpeg."""
    out, _ = (
        ffmpeg.input("pipe:0", format="wav")
        .output(
            "pipe:",
            format="s16le",
            acodec="pcm_s16le",
            ac=1,
            ar=audio_settings.SAMPLE_RATE,
        )
        .run(input=wav_bytes.getvalue(), capture_stdout=True, capture_stderr=True)
    )
    return (
        np.frombuffer(out, dtype=np.int16).astype(np.float32)
        / noise_detection_settings.INT16_MAX
    )


def _seconds_to_samples(seconds: float) -> int:
    """Convert a time position in seconds to a sample index."""
    return int(seconds * audio_settings.SAMPLE_RATE)


def compute_spectral_flatness_on_silences(
    wav_bytes: BytesIO,
) -> float | None:
    """Calculate the average spectral flatness over silence segments."""
    normalized_wav_bytes = two_pass_volume_normalization(wav_bytes)
    silences = _detect_silences(normalized_wav_bytes)
    samples = _read_audio_samples(normalized_wav_bytes)

    flatness_values = []
    for seg_start, seg_end in silences:
        segment = samples[_seconds_to_samples(seg_start) : _seconds_to_samples(seg_end)]
        if len(segment) < noise_detection_settings.FRAME_SIZE:
            continue
        for start in range(
            0,
            len(segment) - noise_detection_settings.FRAME_SIZE,
            noise_detection_settings.HOP_SIZE,
        ):
            frame = segment[start : start + noise_detection_settings.FRAME_SIZE]
            spectrum = np.abs(np.fft.rfft(frame)) ** 2 + 1e-12
            geo_mean = np.exp(np.mean(np.log(spectrum)))
            arith_mean = np.mean(spectrum)
            flatness_values.append(geo_mean / arith_mean)

    return float(np.mean(flatness_values)) if flatness_values else None


def is_audio_noisy(wav_bytes: BytesIO) -> bool:
    """Determine whether audio is noisy based on spectral flatness in silence segments."""
    flatness = compute_spectral_flatness_on_silences(wav_bytes)
    if flatness is None:
        logger.warning(
            "No silence segments detected, cannot compute spectral flatness. Assuming noisy audio."
        )
    wav_bytes.seek(0)
    return (
        flatness is None or flatness > noise_detection_settings.NOISE_FLATNESS_THRESHOLD
    )
