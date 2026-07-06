from loguru import logger

from mcr_meeting.app.domain.transcription.chunking import compute_transcription_chunks
from mcr_meeting.app.domain.transcription.vad import diarize_vad_transcription_segments
from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.infrastructure import s3
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor


def run_transcribe_chunks(
    meeting_id: int,
    transcription_processor: TranscriptionProcessor,
) -> None:
    diarization = s3.read_diarization(meeting_id)

    if not diarization:
        logger.warning("No diarization result. Writing empty transcription.")
        s3.write_transcription_raw(meeting_id, [])
        return

    transcription_chunk_spans = compute_transcription_chunks(diarization)

    transcription_segments = transcription_processor.transcribe(
        audio_bytes=s3.read_preprocessed_audio(meeting_id),
        chunk_spans=transcription_chunk_spans,
    )

    diarized_transcription_segments = diarize_vad_transcription_segments(
        transcription_segments, diarization
    )

    if not diarized_transcription_segments:
        logger.warning("No transcription segments found")
        raise InvalidAudioFileError("No transcription segments found")

    s3.write_transcription_raw(meeting_id, diarized_transcription_segments)
