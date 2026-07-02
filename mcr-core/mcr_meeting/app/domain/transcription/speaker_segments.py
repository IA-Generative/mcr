"""Build speaker transcriptions and map speaker labels to participant names."""

import re

from loguru import logger

from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    Participant,
    SpeakerTranscription,
)


def convert_to_french_speaker(speaker_label: str) -> str:
    """Convert speaker labels to French format"""
    return re.sub(r"SPEAKER_(\d+)", r"LOCUTEUR_\1", speaker_label)


def replace_speaker_name_if_available(
    segments: list[DiarizedTranscriptionSegment], participants: list[Participant]
) -> None:
    speaker_id_to_speaker_name = {p.speaker_id: p.name for p in participants if p.name}
    logger.info("speaker_id_to_speaker_name {}", speaker_id_to_speaker_name)

    for segment in segments:
        segment.speaker = speaker_id_to_speaker_name.get(
            segment.speaker, segment.speaker
        )


def build_speaker_transcriptions(
    meeting_id: int, segments: list[DiarizedTranscriptionSegment]
) -> list[SpeakerTranscription]:
    return [
        SpeakerTranscription(
            meeting_id=meeting_id,
            transcription_index=segment.id,
            speaker=segment.speaker,
            transcription=segment.text,
            start=segment.start,
            end=segment.end,
        )
        for segment in segments
    ]
