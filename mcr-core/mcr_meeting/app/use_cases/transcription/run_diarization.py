from mcr_meeting.app.infrastructure import s3
from mcr_meeting.app.infrastructure.diarization import DiarizationProcessor
from mcr_meeting.app.use_cases.transcription._shared.preprocess_audio import (
    preprocess_audio,
)


def run_diarization(
    meeting_id: int, diarization_processor: DiarizationProcessor
) -> None:
    audio_bytes = s3.fetch_audio_bytes(meeting_id)
    preprocessed_audio = preprocess_audio(audio_bytes)
    diarization = diarization_processor.diarize(audio_bytes=preprocessed_audio)
    s3.write_preprocessed_audio(meeting_id, preprocessed_audio)
    s3.write_diarization(meeting_id, diarization)
