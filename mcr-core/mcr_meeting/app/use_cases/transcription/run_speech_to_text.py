from io import BytesIO

from loguru import logger

from mcr_meeting.app.infrastructure.diarization import DiarizationProcessor
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.use_cases.transcription._shared.post_process_segments import (
    post_process_segments,
)
from mcr_meeting.app.use_cases.transcription._shared.preprocess_audio import (
    preprocess_audio,
)
from mcr_meeting.app.use_cases.transcription._shared.transcribe_diarized_audio import (
    transcribe_diarized_audio,
)


def run_speech_to_text(
    audio_bytes: BytesIO,
    diarization_processor: DiarizationProcessor,
    transcription_processor: TranscriptionProcessor,
) -> list[DiarizedTranscriptionSegment]:
    preprocessed_audio = preprocess_audio(audio_bytes)

    diarization = diarization_processor.diarize(audio_bytes=preprocessed_audio)
    if not diarization:
        logger.warning("No diarization result. Returning empty transcription.")
        return []

    segments = transcribe_diarized_audio(
        preprocessed_audio, diarization, transcription_processor
    )

    return post_process_segments(segments)
