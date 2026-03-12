"""
Utility functions for transcription processing.
"""

import re
from itertools import groupby

from loguru import logger

from mcr_meeting.app.configs.base import TranscriptionForbiddenSentences
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment


def merge_consecutive_segments_per_speaker(
    transcriptions: list[DiarizedTranscriptionSegment],
) -> list[DiarizedTranscriptionSegment]:
    """
    Merge consecutive speaker segments into a single segment for each speaker.

    Args:
        transcriptions (List[DiarizedTranscriptionSegment]): A list of DiarizedTranscriptionSegment objects
            representing the transcriptions to be merged.

    Returns:
        List[DiarizedTranscriptionSegment]: A new list of DiarizedTranscriptionSegment objects with merged
            transcriptions for consecutive speakers.
    """
    logger.debug("Merging consecutive speaker segments...")
    merged_transcriptions: list[DiarizedTranscriptionSegment] = []

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


def remove_hallucinations(
    segments: list[DiarizedTranscriptionSegment],
) -> list[DiarizedTranscriptionSegment]:
    """
    Remove hallucinations from the transcription.

    Args:
        segments (list[DiarizedTranscriptionSegment]): A list of DiarizedTranscriptionSegment objects
            representing the transcription's segments to be cleaned.

    Returns:
        list[DiarizedTranscriptionSegment]: A new list of DiarizedTranscriptionSegment objects with hallucinations
            removed.
    """
    forbidden_sentences = TranscriptionForbiddenSentences()
    pattern = re.compile(
        "|".join(re.escape(s) for s in forbidden_sentences.FORBIDDEN_SENTENCES)
    )

    cleaned_segments = []

    for segment in segments:
        # Remove forbidden strings
        segment.text = pattern.sub("", segment.text)

        # Clean whitespace
        segment.text = " ".join(segment.text.split())

        # Keep only non-empty segments
        if segment.text:
            cleaned_segments.append(segment)

    return cleaned_segments
