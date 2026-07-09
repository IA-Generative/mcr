from collections.abc import Callable

from loguru import logger

from mcr_meeting.app.domain.transcription.post_process import (
    merge_consecutive_segments_per_speaker,
    remove_hallucinations,
)
from mcr_meeting.app.domain.transcription.text_chunking import (
    chunk_text,
    format_segments_for_llm,
    reassemble_corrected_segments,
)
from mcr_meeting.app.infrastructure.llm.acronyms import correct_acronyms
from mcr_meeting.app.infrastructure.llm.spelling import correct_spelling
from mcr_meeting.app.infrastructure.unleash import (
    FeatureFlag,
    get_feature_flag_client,
)
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment


def post_process_segments(
    segments: list[DiarizedTranscriptionSegment],
) -> list[DiarizedTranscriptionSegment]:
    merged_segments = merge_consecutive_segments_per_speaker(segments)
    cleaned_segments = remove_hallucinations(merged_segments)

    logger.debug("Acronym correction: correcting segments")
    cleaned_segments = _apply_text_correction(cleaned_segments, correct_acronyms)

    if get_feature_flag_client().is_enabled(FeatureFlag.SPELLING_CORRECTION):
        logger.debug("Spelling correction enabled, correcting segments")
        cleaned_segments = _apply_text_correction(cleaned_segments, correct_spelling)
    else:
        logger.debug("Spelling correction disabled, skipping correction")

    return cleaned_segments


def _apply_text_correction(
    segments: list[DiarizedTranscriptionSegment],
    correct_chunk: Callable[[str], str],
) -> list[DiarizedTranscriptionSegment]:
    if not segments:
        return []
    text = format_segments_for_llm(segments)
    chunks = chunk_text(text, chunk_overlap=0)
    corrected_chunks = [correct_chunk(chunk) for chunk in chunks]
    return reassemble_corrected_segments(corrected_chunks, segments)
