"""
This module provide function to implement diarisation pipeline
"""

from mcr_meeting.app.schemas.transcription_schema import (
    SpeakerTranscription,
)
from mcr_meeting.app.use_cases.transcription.run_diarization import run_diarization
from mcr_meeting.app.use_cases.transcription.run_finalize_transcription import (
    run_finalize_transcription,
)
from mcr_meeting.app.use_cases.transcription.run_transcribe_chunks import (
    run_transcribe_chunks,
)


def transcribe_meeting(
    meeting_id: int,
) -> list[SpeakerTranscription]:
    artifact = run_diarization(meeting_id)
    segments = run_transcribe_chunks(artifact)
    return run_finalize_transcription(meeting_id, segments)
