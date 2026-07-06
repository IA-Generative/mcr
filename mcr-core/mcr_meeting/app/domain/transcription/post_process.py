"""Pure post-processing of diarized transcription segments."""

import re
from itertools import groupby

from loguru import logger

from mcr_meeting.app.configs.base import TranscriptionForbiddenSentences
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment


def merge_consecutive_segments_per_speaker(
    transcriptions: list[DiarizedTranscriptionSegment],
) -> list[DiarizedTranscriptionSegment]:
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
    forbidden_sentences = TranscriptionForbiddenSentences()
    pattern = re.compile(
        "|".join(re.escape(s) for s in forbidden_sentences.FORBIDDEN_SENTENCES)
    )

    cleaned_segments = []

    for segment in segments:
        segment.text = pattern.sub("", segment.text)

        segment.text = " ".join(segment.text.split())

        if segment.text:
            cleaned_segments.append(segment)

    return cleaned_segments
