from loguru import logger

from mcr_meeting.app.domain.transcription.speaker_segments import (
    replace_speaker_name_if_available,
)
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
)
from mcr_meeting.app.services.speech_to_text.participants_naming import (
    ParticipantExtraction,
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
        extractor = ParticipantExtraction()
        participants = extractor.extract(segments)
        replace_speaker_name_if_available(segments, participants)

        logger.debug("Extracted {} participants' names", len(participants))
    except Exception as e:
        logger.warning("Failed to extract participants: {}", e)
        pass
