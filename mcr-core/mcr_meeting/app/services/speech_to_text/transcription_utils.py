"""
Utility functions for transcription processing.
"""

from itertools import groupby
from typing import List

from loguru import logger

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment


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
