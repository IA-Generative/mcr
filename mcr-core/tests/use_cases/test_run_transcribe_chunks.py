import json
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

import mcr_meeting.app.use_cases.transcription.run_transcribe_chunks as rtc
from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from tests.mocks.in_memory_s3 import InMemoryS3

MEETING_ID = 123

# Clés écrites en dur : elles font partie du contrat d'interface de l'app
# vers S3, un changement ici casse la reprise des pipelines en vol.
PREPROCESSED_KEY = "artifacts/123/preprocessed_audio.wav"
DIARIZATION_KEY = "artifacts/123/diarization.json"
TRANSCRIPTION_RAW_KEY = "artifacts/123/transcription_raw.json"

_RAW_SEGMENTS = [
    DiarizedTranscriptionSegment(id=0, start=0.0, end=1.0, text="hello", speaker="A")
]


def _seed_diarization_artifacts(in_memory_s3: InMemoryS3) -> None:
    in_memory_s3.objects[PREPROCESSED_KEY] = b"wav-data"
    in_memory_s3.objects[DIARIZATION_KEY] = (
        b'[{"start": 0.0, "end": 1.0, "speaker": "A"}]'
    )


def test_reads_diarization_artifacts_and_writes_raw_segments(
    in_memory_s3: InMemoryS3, mocker: MockerFixture
) -> None:
    _seed_diarization_artifacts(in_memory_s3)
    processor = Mock()
    mocker.patch.object(
        rtc, "diarize_vad_transcription_segments", return_value=_RAW_SEGMENTS
    )

    rtc.run_transcribe_chunks(MEETING_ID, processor)

    audio_bytes = processor.transcribe.call_args.kwargs["audio_bytes"]
    assert audio_bytes.getvalue() == b"wav-data"
    assert json.loads(in_memory_s3.objects[TRANSCRIPTION_RAW_KEY]) == [
        {"id": 0, "start": 0.0, "end": 1.0, "text": "hello", "speaker": "A"}
    ]


def test_empty_diarization_writes_empty_raw_without_transcribing(
    in_memory_s3: InMemoryS3,
) -> None:
    in_memory_s3.objects[DIARIZATION_KEY] = b"[]"
    processor = Mock()

    rtc.run_transcribe_chunks(MEETING_ID, processor)

    processor.transcribe.assert_not_called()
    assert json.loads(in_memory_s3.objects[TRANSCRIPTION_RAW_KEY]) == []


def test_raises_and_writes_nothing_when_no_diarized_segments(
    in_memory_s3: InMemoryS3, mocker: MockerFixture
) -> None:
    _seed_diarization_artifacts(in_memory_s3)
    mocker.patch.object(rtc, "diarize_vad_transcription_segments", return_value=[])

    with pytest.raises(InvalidAudioFileError):
        rtc.run_transcribe_chunks(MEETING_ID, Mock())

    assert TRANSCRIPTION_RAW_KEY not in in_memory_s3.objects
