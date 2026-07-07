import json

from mcr_meeting.app.infrastructure.s3 import (
    get_full_transcript_object_name,
    write_full_transcript,
)
from mcr_meeting.app.schemas.transcription_schema import (
    FullTranscript,
    SpeakerTranscription,
)
from tests.mocks.in_memory_s3 import InMemoryS3

MEETING_ID = 123

FULL_TRANSCRIPT_KEY = "transcription/123/full_transcript.json"


def _speaker_transcriptions() -> list[SpeakerTranscription]:
    return [
        SpeakerTranscription(
            meeting_id=MEETING_ID,
            speaker="LOCUTEUR_00",
            transcription_index=0,
            transcription="bonjour",
            start=0.0,
            end=12.5,
        ),
        SpeakerTranscription(
            meeting_id=MEETING_ID,
            speaker="LOCUTEUR_01",
            transcription_index=1,
            transcription="salut",
            start=12.5,
            end=28.3,
        ),
    ]


def test_full_transcript_object_name_matches_contract() -> None:
    assert get_full_transcript_object_name(MEETING_ID) == FULL_TRANSCRIPT_KEY


def test_from_speaker_transcriptions_maps_segments() -> None:
    full_transcript = FullTranscript.from_speaker_transcriptions(
        MEETING_ID, _speaker_transcriptions()
    )

    assert full_transcript.meeting_id == MEETING_ID
    assert full_transcript.version == 0
    assert [s.speaker for s in full_transcript.segments] == [
        "LOCUTEUR_00",
        "LOCUTEUR_01",
    ]
    assert full_transcript.segments[0].transcription == "bonjour"
    assert full_transcript.segments[1].start == 12.5


def test_from_speaker_transcriptions_with_empty_list() -> None:
    full_transcript = FullTranscript.from_speaker_transcriptions(MEETING_ID, [])

    assert full_transcript.meeting_id == MEETING_ID
    assert full_transcript.segments == []


def test_write_full_transcript_puts_json_at_contract_key(
    in_memory_s3: InMemoryS3,
) -> None:
    full_transcript = FullTranscript.from_speaker_transcriptions(
        MEETING_ID, _speaker_transcriptions()
    )

    write_full_transcript(full_transcript)

    written = json.loads(in_memory_s3.objects[FULL_TRANSCRIPT_KEY])
    assert written["meeting_id"] == MEETING_ID
    assert written["version"] == 0
    assert written["segments"] == [
        {
            "speaker": "LOCUTEUR_00",
            "transcription_index": 0,
            "transcription": "bonjour",
            "start": 0.0,
            "end": 12.5,
        },
        {
            "speaker": "LOCUTEUR_01",
            "transcription_index": 1,
            "transcription": "salut",
            "start": 12.5,
            "end": 28.3,
        },
    ]
