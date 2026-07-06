from collections.abc import Callable

from langfuse import observe
from loguru import logger

from mcr_meeting.app.configs.base import ChunkingConfig
from mcr_meeting.app.domain.transcription.participant_reconciliation import (
    ParticipantNameLoss,
    detect_name_losses,
    format_participants_input,
)
from mcr_meeting.app.domain.transcription.post_process import (
    merge_consecutive_segments_per_speaker,
    remove_hallucinations,
)
from mcr_meeting.app.domain.transcription.speaker_segments import (
    build_speaker_transcriptions,
    replace_speaker_name_if_available,
)
from mcr_meeting.app.domain.transcription.text_chunking import (
    chunk_text,
    format_segments_for_llm,
    reassemble_corrected_segments,
)
from mcr_meeting.app.infrastructure import s3
from mcr_meeting.app.infrastructure.llm.acronyms import correct_acronyms
from mcr_meeting.app.infrastructure.llm.participants import (
    extract_participants,
    refine_participants,
)
from mcr_meeting.app.infrastructure.llm.spelling import correct_spelling
from mcr_meeting.app.infrastructure.unleash import (
    FeatureFlag,
    get_feature_flag_client,
)
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    Participant,
    SpeakerTranscription,
)
from mcr_meeting.app.utils.langfuse_observability import (
    record_participant_name_lost_event,
)


def run_finalize_transcription(meeting_id: int) -> list[SpeakerTranscription]:
    segments = s3.read_transcription_raw(meeting_id)
    cleaned_segments = _post_process(segments)
    _enrich_with_participants(cleaned_segments)
    return build_speaker_transcriptions(meeting_id, cleaned_segments)


def _post_process(
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


def _enrich_with_participants(
    segments: list[DiarizedTranscriptionSegment],
) -> None:
    try:
        participants = _extract_participants(segments)
        replace_speaker_name_if_available(segments, participants)
        logger.debug("Extracted {} participants' names", len(participants))
    except Exception as e:
        logger.warning("Failed to extract participants: {}", e)


@observe(name="participant_extraction")
def _extract_participants(
    segments: list[DiarizedTranscriptionSegment],
) -> list[Participant]:
    text = format_participants_input(segments)
    chunks = chunk_text(text, chunk_overlap=ChunkingConfig().CHUNK_OVERLAP)

    if not chunks:
        logger.warning("No chunks found")
        return []

    participants = extract_participants(chunks[0])

    for step_index, chunk in enumerate(chunks[1:], start=1):
        previous = participants
        participants = refine_participants(participants, chunk)
        for loss in detect_name_losses(previous, participants, step_index):
            _log_name_loss(loss)

    return participants


def _log_name_loss(loss: ParticipantNameLoss) -> None:
    if loss.reason == "disappeared":
        logger.warning(
            "Participant {} (name={!r}) disappeared from the list at step {}",
            loss.speaker_id,
            loss.previous_name,
            loss.step_index,
        )
    else:
        logger.warning(
            "Participant {} lost their name at step {} (was {!r})",
            loss.speaker_id,
            loss.step_index,
            loss.previous_name,
        )
    record_participant_name_lost_event(
        speaker_id=loss.speaker_id,
        step_index=loss.step_index,
        previous_name=loss.previous_name,
        reason=loss.reason,
    )
