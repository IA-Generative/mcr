"""Pure validation rules for ASR evaluation archives (no I/O)."""

import zipfile
from collections.abc import Sequence
from io import BytesIO

from mcr_meeting.app.exceptions.exceptions import InvalidEvaluationZipError

RAW_AUDIOS_DIR = "raw_audios/"
REFERENCE_TRANSCRIPTS_DIR = "reference_transcripts/"


def is_zip_filename(filename: str | None) -> bool:
    return filename is not None and filename.endswith(".zip")


def validate_evaluation_zip_structure(
    zip_bytes: bytes, supported_audio_formats: Sequence[str]
) -> None:
    try:
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as archive:
            files = archive.namelist()
    except zipfile.BadZipFile as exc:
        raise InvalidEvaluationZipError(
            "Corrupted file. Please upload a valid zip file."
        ) from exc

    has_audio_dir = any(
        RAW_AUDIOS_DIR in name
        and any(name.endswith(f".{fmt}") for fmt in supported_audio_formats)
        for name in files
    )
    has_reference_dir = any(
        REFERENCE_TRANSCRIPTS_DIR in name and name.endswith(".json") for name in files
    )

    if not has_audio_dir or not has_reference_dir:
        supported = " or ".join(f".{fmt}" for fmt in supported_audio_formats)
        raise InvalidEvaluationZipError(
            f"Zip file must contain '{RAW_AUDIOS_DIR}' with {supported} files and "
            f"'{REFERENCE_TRANSCRIPTS_DIR}' with .json files at the root level."
        )
