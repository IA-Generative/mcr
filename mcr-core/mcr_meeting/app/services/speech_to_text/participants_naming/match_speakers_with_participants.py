from loguru import logger

from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
)
from mcr_meeting.app.services.speech_to_text.participants_naming import (
    ParticipantExtraction,
)
from mcr_meeting.app.services.speech_to_text.participants_naming.participant_extraction import (
    Participant,
)


def format_segments_for_llm(segments: list[DiarizedTranscriptionSegment]) -> str:
    """
    Helper to convert segments into a dialogue string.

    Args:
        segments (list[DiarizedTranscriptionSegment]): List of speaker transcriptions.

    Returns:
        str: Dialogue string.
    """
    return "\n".join([str(seg) for seg in segments])


def replace_speaker_name_if_available(
    segments: list[DiarizedTranscriptionSegment], participants: list[Participant]
) -> None:
    """Replaces speaker IDs with real names where available."""
    # Build the map once: { "SPEAKER_01": "John Doe" }
    speaker_id_to_speaker_name = {p.speaker_id: p.name for p in participants if p.name}
    logger.info("speaker_id_to_speaker_name {}", speaker_id_to_speaker_name)

    for segment in segments:
        segment.speaker = speaker_id_to_speaker_name.get(
            segment.speaker, segment.speaker
        )


def enrich_segments_with_participants(
    segments: list[DiarizedTranscriptionSegment],
) -> None:
    """
    Add participants to segments.

    Args:
        segments (list[DiarizedTranscriptionSegment]): List of speaker transcriptions.

    Returns:
        None
    """
    try:
        # formatting for LLM
        dialogue_text = format_segments_for_llm(segments)

        extractor = ParticipantExtraction()
        participants = extractor.extract(dialogue_text)
        replace_speaker_name_if_available(segments, participants)

        logger.debug("Extracted {} participants' names", len(participants))
    except Exception as e:
        logger.warning("Failed to extract participants: {}", e)
        pass
