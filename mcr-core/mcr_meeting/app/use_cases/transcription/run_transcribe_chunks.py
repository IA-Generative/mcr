from loguru import logger

from mcr_meeting.app.infrastructure import s3
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.use_cases.transcription._shared.transcribe_diarized_audio import (
    transcribe_diarized_audio,
)


def run_transcribe_chunks(
    meeting_id: int,
    transcription_processor: TranscriptionProcessor,
) -> None:
    diarization = s3.read_diarization(meeting_id)

    if not diarization:
        logger.warning("No diarization result. Writing empty transcription.")
        s3.write_transcription_raw(meeting_id, [])
        return

    diarized_transcription_segments = transcribe_diarized_audio(
        s3.read_preprocessed_audio(meeting_id),
        diarization,
        transcription_processor,
    )

    s3.write_transcription_raw(meeting_id, diarized_transcription_segments)
