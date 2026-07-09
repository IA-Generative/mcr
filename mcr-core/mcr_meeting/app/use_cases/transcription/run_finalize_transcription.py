from loguru import logger

from mcr_meeting.app.domain.transcription.speaker_segments import (
    build_speaker_transcriptions,
    replace_speaker_name_if_available,
)
from mcr_meeting.app.infrastructure import s3
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    FullTranscript,
    SpeakerTranscription,
)
from mcr_meeting.app.use_cases.transcription._shared.extract_participants import (
    extract_participants,
)
from mcr_meeting.app.use_cases.transcription._shared.post_process_segments import (
    post_process_segments,
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
        participants = extract_participants(segments)
        replace_speaker_name_if_available(segments, participants)
        logger.debug("Extracted {} participants' names", len(participants))
    except Exception as e:
        logger.warning("Failed to extract participants: {}", e)
