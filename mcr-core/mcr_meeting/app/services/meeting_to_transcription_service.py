"""
This module provide function to implement diarisation pipeline
"""

from io import BytesIO
from itertools import groupby
from typing import List

from loguru import logger

from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    SpeakerTranscription,
)
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    download_and_concatenate_s3_audio_chunks_into_bytes,
)
from mcr_meeting.app.services.s3_service import (
    get_objects_list_from_prefix,
)
from mcr_meeting.app.services.transcription_engine_service import (
    speech_to_text_transcription,
)


def merge_consecutive_segments_per_speaker(
    transcriptions: List[DiarizedTranscriptionSegment],
) -> List[DiarizedTranscriptionSegment]:
    """
    Merge consecutive speaker segments into a single segment for each speaker.

    Args:
        transcriptions (List[DiarizedTranscriptionSegment]): A list of DiarizedTranscriptionSegment objects
            representing the transcriptions to be merged.

    Returns:
        List[DiarizedTranscriptionSegment]: A new list of DiarizedTranscriptionSegment objects with merged
            transcriptions for consecutive speakers.
    """
    logger.info("Merging consecutive speaker segments...")
    merged_transcriptions: List[DiarizedTranscriptionSegment] = []

    for i, (speaker, group) in enumerate(
        groupby(transcriptions, key=lambda x: x.speaker)
    ):
        group_list = list(group)
        merged_transcriptions.append(
            DiarizedTranscriptionSegment(
                id=i,
                speaker=speaker,
                text=" ".join(item.text for item in group_list),
                start=group_list[0].start,
                end=group_list[-1].end,
            )
        )

    return merged_transcriptions


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
        InvalidAudioFileError: If no audio files are found or processing fails.
    """

    logger.info("Fetching audio bytes for meeting ID: {}", meeting_id)

    try:
        s3_chunk_iterator = get_objects_list_from_prefix(prefix=f"{meeting_id}/")

        audio_bytes = download_and_concatenate_s3_audio_chunks_into_bytes(
            s3_chunk_iterator
        )
        return audio_bytes

    except ValueError as no_files_error:
        logger.error(
            "No audio files found for meeting {}: {}", meeting_id, no_files_error
        )
        raise ValueError(
            f"No audio files found for meeting {meeting_id}: {no_files_error}"
        )
    except InvalidAudioFileError as audio_processing_error:
        logger.error(
            "Audio processing failed for meeting {}: {}",
            meeting_id,
            audio_processing_error,
        )
        raise InvalidAudioFileError(
            f"Audio processing failed for meeting {meeting_id}: {audio_processing_error}"
        )
    except Exception as fetch_error:
        logger.error(
            "Failed to fetch audio bytes for meeting {}: {}", meeting_id, fetch_error
        )
        raise Exception(
            f"Failed to fetch audio bytes for meeting {meeting_id}: {fetch_error}"
        )


def transcribe_meeting(
    meeting_id: int,
) -> List[SpeakerTranscription]:
    """
    Pipeline for transcription and diarization. Matches Whisper transcription segments
    with speaker timestamps and assigns the most represented speaker.

    Args:
        meeting_id (int): Meeting ID.

    Returns:
        List[SpeakerTranscription]: List of transcriptions associated with speakers.
        None: If transcription fails or no audio is available.
    """

    try:
        full_audio_bytes = fetch_audio_bytes(meeting_id)

        if not full_audio_bytes:
            logger.error("Could not fetch audio bytes for meeting {}", meeting_id)
            raise InvalidAudioFileError(
                f"Could not fetch audio bytes for meeting {meeting_id}"
            )

        transcription_with_speech = speech_to_text_transcription(full_audio_bytes)

        if not transcription_with_speech:
            logger.warning("No transcription segments found for meeting {}", meeting_id)
            raise InvalidAudioFileError(
                f"No transcription segments found for meeting {meeting_id}"
            )

        merged_segments = merge_consecutive_segments_per_speaker(
            transcription_with_speech
        )

        # Convert merged DiarizedTranscriptionSegment to SpeakerTranscription for return
        speaker_transcription_segments = [
            SpeakerTranscription(
                meeting_id=meeting_id,
                transcription_index=segment.id,
                speaker=segment.speaker,
                transcription=segment.text,
                start=segment.start,
                end=segment.end,
            )
            for segment in merged_segments
        ]

        return speaker_transcription_segments

    except Exception as transcription_error:
        logger.exception(
            "Transcription failed for meeting {}: {}", meeting_id, transcription_error
        )
        raise InvalidAudioFileError(
            f"Transcription failed for meeting {meeting_id}"
        ) from transcription_error
