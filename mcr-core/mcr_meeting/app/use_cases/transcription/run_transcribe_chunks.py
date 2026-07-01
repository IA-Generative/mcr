from loguru import logger

from mcr_meeting.app.domain.transcription.chunking import compute_transcription_chunks
from mcr_meeting.app.domain.transcription.vad import diarize_vad_transcription_segments
from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.use_cases.transcription._shared.artifacts import (
    DiarizationArtifact,
)


def run_transcribe_chunks(
    artifact: DiarizationArtifact,
) -> list[DiarizedTranscriptionSegment]:
    if not artifact.diarization:
        logger.warning("No diarization result. Returning empty transcription.")
        return []

    transcription_chunk_spans = compute_transcription_chunks(artifact.diarization)

    transcription_segments = TranscriptionProcessor().transcribe(
        audio_bytes=artifact.preprocessed_audio,
        chunk_spans=transcription_chunk_spans,
    )

    diarized_transcription_segments = diarize_vad_transcription_segments(
        transcription_segments, artifact.diarization
    )

    if not diarized_transcription_segments:
        logger.warning("No transcription segments found")
        raise InvalidAudioFileError("No transcription segments found")

    return diarized_transcription_segments
