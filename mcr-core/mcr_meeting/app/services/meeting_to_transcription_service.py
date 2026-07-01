"""
This module provide function to implement diarisation pipeline
"""

from mcr_meeting.app.infrastructure.s3 import fetch_audio_bytes
from mcr_meeting.app.schemas.transcription_schema import (
    SpeakerTranscription,
)
from mcr_meeting.app.services.speech_to_text.participants_naming.match_speakers_with_participants import (
    enrich_segments_with_participants,
)
from mcr_meeting.app.services.speech_to_text.speech_to_text import (
    SpeechToTextPipeline,
)

speech_to_text_pipeline = SpeechToTextPipeline()


def transcribe_meeting(
    meeting_id: int,
) -> list[SpeakerTranscription]:
    """
    Pipeline for transcription and diarization. Matches Whisper transcription segments
    with speaker timestamps and assigns the most represented speaker.

    Args:
        meeting_id (int): Meeting ID.

    Returns:
        list[SpeakerTranscription]: List of transcriptions associated with speakers.
    """

    full_audio_bytes = fetch_audio_bytes(meeting_id)

    diarized_transcription_segments = speech_to_text_pipeline.run(full_audio_bytes)

    enrich_segments_with_participants(diarized_transcription_segments)

    speaker_transcription_segments = [
        SpeakerTranscription(
            meeting_id=meeting_id,
            transcription_index=segment.id,
            speaker=segment.speaker,
            transcription=segment.text,
            start=segment.start,
            end=segment.end,
        )
        for segment in diarized_transcription_segments
    ]

    return speaker_transcription_segments
