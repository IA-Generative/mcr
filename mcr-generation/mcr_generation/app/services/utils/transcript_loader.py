import posixpath

from loguru import logger

from mcr_generation.app.exceptions.exceptions import TranscriptionFileNotFoundError
from mcr_generation.app.schemas.transcript import FullTranscript
from mcr_generation.app.services.utils.input_chunker import (
    Chunk,
    chunk_docx_to_document_list,
    chunk_transcript_to_document_list,
)
from mcr_generation.app.services.utils.s3_service import get_file_from_s3

FULL_TRANSCRIPT_FILENAME = "full_transcript.json"


def load_transcript_chunks(transcription_object_filename: str) -> list[Chunk]:
    chunks = _try_load_full_transcript(transcription_object_filename)
    if chunks is not None:
        return chunks

    docx_bytes = get_file_from_s3(transcription_object_filename)
    return chunk_docx_to_document_list(docx_bytes)


def _try_load_full_transcript(
    transcription_object_filename: str,
) -> list[Chunk] | None:
    object_name = posixpath.join(
        posixpath.dirname(transcription_object_filename), FULL_TRANSCRIPT_FILENAME
    )
    try:
        raw = get_file_from_s3(object_name)
    except TranscriptionFileNotFoundError:
        logger.warning(
            "Full transcript not found at {}; falling back to the DOCX", object_name
        )
        return None

    return chunk_transcript_to_document_list(
        FullTranscript.model_validate_json(raw.getvalue())
    )
