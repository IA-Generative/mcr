"""
This module provide function to implement diarisation pipeline
"""

from io import BytesIO

from loguru import logger

from mcr_meeting.app.exceptions.exceptions import (
    InvalidAudioFileError,
    NoAudioFoundError,
)
from mcr_meeting.app.schemas.transcription_schema import (
    SpeakerTranscription,
)
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    download_and_concatenate_s3_audio_chunks_into_bytes,
)
from mcr_meeting.app.services.feature_flag_service import get_feature_flag_client
from mcr_meeting.app.services.s3_service import (
    get_objects_list_from_prefix,
)
from mcr_meeting.app.services.speech_to_text.participants_naming.match_speakers_with_participants import (
    enrich_segments_with_participants,
)
from mcr_meeting.app.services.speech_to_text.speech_to_text import (
    SpeechToTextPipeline,
)

speech_to_text_pipeline = SpeechToTextPipeline()


def fetch_audio_bytes(
    meeting_id: int,
) -> BytesIO:
    """
    Fetch audio bytes from normalized S3 audio chunks for a given meeting ID.

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        bytes: The audio bytes for the specified meeting.

    Raises:
        NoAudioFoundError: If no audio files are found for the meeting.
        InvalidAudioFileError: If audio processing fails or an unexpected error occurs.
    """

    logger.info("Fetching audio bytes for meeting ID: {}", meeting_id)

    try:
        s3_chunk_iterator = get_objects_list_from_prefix(prefix=f"{meeting_id}/")

        audio_bytes = download_and_concatenate_s3_audio_chunks_into_bytes(
            s3_chunk_iterator
        )
        return audio_bytes

    except NoAudioFoundError as no_files_error:
        logger.error(
            "No audio files found for meeting {}: {}", meeting_id, no_files_error
        )
        raise NoAudioFoundError(
            f"No audio files found for meeting {meeting_id}"
        ) from no_files_error

    except Exception as fetch_error:
        logger.error(
            "Failed to fetch audio bytes for meeting {}: {}", meeting_id, fetch_error
        )
        raise InvalidAudioFileError(
            f"Failed to fetch audio bytes for meeting {meeting_id}: {fetch_error}"
        ) from fetch_error


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

    diarized_transcription_segments = speech_to_text_pipeline.run(
        full_audio_bytes, meeting_id
    )

    feature_flag_client = get_feature_flag_client()

    if feature_flag_client.is_enabled("speaker_identification"):
        logger.info("Speaker identification enabled, enriching segments")
        enrich_segments_with_participants(diarized_transcription_segments)
    else:
        logger.info("Speaker identification disabled, skipping enrichment")

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
