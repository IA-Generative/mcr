from io import BytesIO

from loguru import logger

from mcr_meeting.app.domain.transcription.chunking import compute_transcription_chunks
from mcr_meeting.app.domain.transcription.vad import diarize_vad_transcription_segments
from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationSegment,
    DiarizedTranscriptionSegment,
)


def transcribe_diarized_audio(
    preprocessed_audio: BytesIO,
    diarization: list[DiarizationSegment],
    transcription_processor: TranscriptionProcessor,
) -> list[DiarizedTranscriptionSegment]:
    transcription_chunk_spans = compute_transcription_chunks(diarization)

    transcription_segments = transcription_processor.transcribe(
        audio_bytes=preprocessed_audio,
        chunk_spans=transcription_chunk_spans,
    )

    diarized_transcription_segments = diarize_vad_transcription_segments(
        transcription_segments, diarization
    )

    if not diarized_transcription_segments:
        logger.warning("No transcription segments found")
        raise InvalidAudioFileError("No transcription segments found")

    return diarized_transcription_segments
