from loguru import logger

from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
)
from mcr_meeting.app.services.speech_to_text.participants_naming import (
    ParticipantExtraction,
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

        logger.debug("Found {} participants", len(participants))
        if not participants:
            logger.debug("No participant found")
        else:
            for p in participants:
                # Logged for this ticket, will be removed later
                logger.debug("--- Participant ---")
                logger.debug("ID: {}", p.speaker_id)
                logger.debug("Name: {}", p.name)
                logger.debug("Role: {}", p.role)
                logger.debug("Confidence: {}", p.confidence)
                logger.debug("Justification: {}", p.association_justification)
    except Exception as e:
        logger.warning("Failed to extract participants: {}", e)
        pass
