import os
import tempfile
from io import BytesIO
from typing import Iterator, Optional

import ffmpeg
from loguru import logger

from mcr_meeting.app.configs.base import AudioSettings, Speech2TextSettings
from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.schemas.S3_types import S3Object
from mcr_meeting.app.services.feature_flag_service import FeatureFlagClient
from mcr_meeting.app.services.s3_service import get_file_from_s3
from mcr_meeting.setup.logger import log_ffmpeg_command

s2t_settings = Speech2TextSettings()
audio_settings = AudioSettings()
sample_rate = audio_settings.SAMPLE_RATE
nb_channels = audio_settings.NB_AUDIO_CHANNELS


def normalize_audio_bytes_to_wav_bytes(input_bytes: BytesIO) -> BytesIO:
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
            .global_args("-loglevel", "error")
        )

        log_ffmpeg_command(stream)

        output, error = stream.run(
            capture_stdout=True,
            capture_stderr=True,
        )
        if error:
            logger.error(
                "FFmpeg stderr (bytes→bytes): {}", error.decode(errors="ignore")
            )
            raise InvalidAudioFileError(
                f"FFmpeg normalization (bytes→bytes) failed: {error.decode(errors='ignore')}"
            )
        return BytesIO(output)
    except InvalidAudioFileError:
        # Re-raise our own exceptions
        raise
    except Exception as e:
        logger.error("Unexpected error during normalization: {}", e)
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

        stream = stream.overwrite_output().global_args("-loglevel", "error")

        # Log the generated FFmpeg command for debugging
        try:
            cmd = stream.compile()
            logger.debug("FFmpeg command: %s", " ".join(cmd))
        except Exception:
            pass

        output, error = stream.run(
            input=input_bytes.getvalue(),
            capture_stdout=True,
            capture_stderr=True,
        )
        if error:
            logger.error(
                "FFmpeg stderr (noise filtering): {}", error.decode(errors="ignore")
            )
            raise InvalidAudioFileError(
                f"FFmpeg noise filtering failed: {error.decode(errors='ignore')}"
            )
        return BytesIO(output)
    except InvalidAudioFileError:
        # Re-raise our own exceptions without wrapping them
        raise
    except Exception as e:
        logger.error("Unexpected error during noise filtering: {}", e)
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
        ValueError: If no audio chunks are found
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
            logger.error(
                "Failed to download audio chunk {}: {}",
                obj_info.object_name,
                chunk_error,
            )
            raise InvalidAudioFileError(
                f"Failed to download audio chunk {obj_info.object_name}: {chunk_error}"
            )

    if chunk_count == 0:
        raise ValueError("No audio chunks found in iterator")

    audio_buffer.seek(0)
    return audio_buffer


def assemble_normalized_wav_from_s3_chunks(
    obj_iterator: Iterator[S3Object],
    feature_flag_client: Optional[FeatureFlagClient] = None,
) -> BytesIO:
    """
    Assemble and normalize audio chunks from S3 into a single bytes object.

    Args:
        obj_iterator: Iterator of S3 objects containing audio chunks
        feature_flag_client: Optional feature flag client for checking noise filtering flag

    Returns:
        bytes: Normalized WAV audio bytes ready for transcription
    """

    concatenated_audio_bytes = download_and_concatenate_s3_audio_chunks_into_bytes(
        obj_iterator
    )
    normalized_audio_bytes = normalize_audio_bytes_to_wav_bytes(
        concatenated_audio_bytes
    )

    # Apply noise filtering only if feature flag is enabled
    if feature_flag_client and feature_flag_client.is_enabled("audio_noise_filtering"):
        logger.info("Noise filtering enabled")
        processed_bytes = filter_noise_from_audio_bytes(normalized_audio_bytes)
    else:
        logger.info("Noise filtering disabled, skipping filtering step")
        processed_bytes = normalized_audio_bytes

    return processed_bytes
