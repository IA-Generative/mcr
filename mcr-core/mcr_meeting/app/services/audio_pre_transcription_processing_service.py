from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO, Iterator, Union

import ffmpeg
from loguru import logger

from mcr_meeting.app.configs.base import AudioSettings
from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.schemas.S3_types import S3Object
from mcr_meeting.app.services.s3_service import get_file_from_s3

audio_settings = AudioSettings()
sample_rate = audio_settings.SAMPLE_RATE
nb_channels = audio_settings.NB_AUDIO_CHANNELS
PathLike = Union[str, Path]


def _ffmpeg_normalize_file_to_wav_file(input_path: str, output_path: str) -> None:
    """
    Decode & Re-encode to a single, normalized WAV. Decodes all concatenated segments and
    writes one continuous PCM stream (fixed sample rate/channels), eliminating per-chunk
    timestamp resets (e.g., 0–30s then back to 0) that come from simply appending
    containerized segments.

    This ensures compatibility with speech-to-text (STT) processing by converting the audio
    to a standard format (16 KHz sample rate, single channel).

    Args:
        input_path (str): Path to the input audio file.
        output_path (str): Path to save the re-encoded WAV file.

    Returns:
        None
    """
    ffmpeg.input(input_path).output(  # type: ignore[attr-defined]
        output_path,  # type: ignore[arg-type]
        format="wav",  # type: ignore[call-arg]
        ar=sample_rate,
        ac=nb_channels,
    ).overwrite_output().global_args("-loglevel", "warning").run()  # type: ignore[misc]


def normalize_audio_file_to_wav_bytes(
    input_path: PathLike,
) -> BytesIO:
    """
    Convenience: file→normalized WAV bytes.

    Args:
        input_path (PathLike): Path to the input audio file.
    Returns:
        bytes: Normalized WAV bytes.
    """

    logger.info(
        "Normalizing audio (file→bytes) | sr={} ch={}",
        sample_rate,
        nb_channels,
    )

    with NamedTemporaryFile(suffix=".wav") as out_tmp:
        _ffmpeg_normalize_file_to_wav_file(str(input_path), out_tmp.name)
        out_tmp.seek(0)
        return BytesIO(out_tmp.read())


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

    input = ffmpeg.input("pipe:0", err_detect="ignore_err")

    try:
        output, error = (
            input.output(
                "pipe:1",
                format="wav",
                ar=sample_rate,
                ac=nb_channels,
            )
            .overwrite_output()
            .global_args("-loglevel", "error")
            .run(
                input=input_bytes.getvalue(),
                capture_stdout=True,
                capture_stderr=True,
            )
        )
        if error:
            logger.error(
                "FFmpeg stderr (bytes→bytes): {}", error.decode(errors="ignore")
            )
            raise InvalidAudioFileError(
                f"FFmpeg normalization (bytes→bytes) failed: {error}"
            )
        return BytesIO(output)
    except Exception as e:
        logger.error("Unexpected error during normalization: {}", e)
        raise InvalidAudioFileError(f"Unexpected error during normalization: {e}")


def download_and_concatenate_s3_audio_chunks_into_file(
    obj_iterator: Iterator[S3Object],
    file: IO[bytes],
) -> None:
    """
    Concatenates audio chunks from an S3 object iterator into a single temporary file.

    Args:
        obj_iterator (Iterator[S3Object]): An iterator over S3 objects containing audio chunks.
        file (IO[bytes]): A writable file-like object to store the concatenated audio data.

    Returns:
        None

    Raises:
        InvalidAudioFileError: If no audio chunks are found or S3 download fails
    """
    for obj_info in obj_iterator:
        try:
            audio_chunk_data = get_file_from_s3(object_name=obj_info.object_name)
            file.write(audio_chunk_data.getvalue())
        except Exception as chunk_error:
            logger.error(
                "Failed to download audio chunk {}: {}",
                obj_info.object_name,
                chunk_error,
            )
            raise InvalidAudioFileError(
                f"Failed to download audio chunk {obj_info.object_name}: {chunk_error}"
            )

    file.flush()
    file.seek(0)


def assemble_normalized_wav_from_s3_chunks(
    obj_iterator: Iterator[S3Object], input_extension: str
) -> BytesIO:
    """
    Assemble and normalize audio chunks from S3 into a single WAV bytes object.

    Args:
        obj_iterator: Iterator of S3 objects containing audio chunks
        input_extension: File extension of the audio chunks

    Returns:
        bytes: Normalized WAV audio bytes ready for transcription

    Raises:
        InvalidAudioFileError: If audio processing fails
    """

    with NamedTemporaryFile(suffix=f".{input_extension}") as tmp_input_file:
        download_and_concatenate_s3_audio_chunks_into_file(obj_iterator, tmp_input_file)
        normalized_audio_bytes = normalize_audio_file_to_wav_bytes(tmp_input_file.name)

        return normalized_audio_bytes
