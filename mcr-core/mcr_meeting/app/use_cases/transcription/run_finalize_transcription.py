from langfuse import observe
from loguru import logger

from mcr_meeting.app.configs.base import ChunkingConfig
from mcr_meeting.app.domain.transcription.participant_reconciliation import (
    ParticipantNameLoss,
    detect_name_losses,
    format_segments_as_dialogue,
)
from mcr_meeting.app.domain.transcription.speaker_segments import (
    build_speaker_transcriptions,
    replace_speaker_name_if_available,
)
from mcr_meeting.app.domain.transcription.text_chunking import chunk_text
from mcr_meeting.app.infrastructure import s3
from mcr_meeting.app.infrastructure.llm.participants import (
    extract_participants,
    refine_participants,
)
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    FullTranscript,
    Participant,
    SpeakerTranscription,
)
from mcr_meeting.app.use_cases.transcription._shared.post_process_segments import (
    post_process_segments,
)
from mcr_meeting.app.utils.langfuse_observability import (
    record_participant_name_lost_event,
)


def run_finalize_transcription(meeting_id: int) -> list[SpeakerTranscription]:
    segments = s3.read_transcription_raw(meeting_id)
    cleaned_segments = post_process_segments(segments)
    _enrich_with_participants(cleaned_segments)
    speaker_transcriptions = build_speaker_transcriptions(meeting_id, cleaned_segments)
    s3.write_full_transcript(
        FullTranscript.from_speaker_transcriptions(meeting_id, speaker_transcriptions)
    )
    return speaker_transcriptions


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
    text = format_segments_as_dialogue(segments)
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
