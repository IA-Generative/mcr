from langfuse import observe
from loguru import logger

from mcr_meeting.app.configs.base import ChunkingConfig
from mcr_meeting.app.domain.transcription.participant_reconciliation import (
    ParticipantNameLoss,
    detect_name_losses,
    format_participants_input,
)
from mcr_meeting.app.domain.transcription.speaker_segments import (
    replace_speaker_name_if_available,
)
from mcr_meeting.app.domain.transcription.text_chunking import chunk_text
from mcr_meeting.app.infrastructure.llm.participants import (
    extract_participants,
    refine_participants,
)
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    Participant,
)
from mcr_meeting.app.utils.langfuse_observability import (
    record_participant_name_lost_event,
)


def enrich_segments_with_participants(
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
