"""Build speaker transcriptions and map speaker labels to participant names."""

from loguru import logger

from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    Participant,
    SpeakerTranscription,
)


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
