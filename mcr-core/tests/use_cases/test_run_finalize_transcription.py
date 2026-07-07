import json
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

import mcr_meeting.app.use_cases.transcription.run_finalize_transcription as rf
from tests.mocks.in_memory_s3 import InMemoryS3

MEETING_ID = 123

# Clés écrites en dur : elles font partie du contrat d'interface de l'app
# vers S3, un changement ici casse la reprise des pipelines en vol
# (transcription_raw) ou la lecture par mcr-generation (full_transcript).
TRANSCRIPTION_RAW_KEY = "artifacts/123/transcription_raw.json"
FULL_TRANSCRIPT_KEY = "transcription/123/full_transcript.json"


def _setup_pipeline(in_memory_s3: InMemoryS3, mocker: MockerFixture) -> None:
    in_memory_s3.objects[TRANSCRIPTION_RAW_KEY] = (
        b'[{"id": 0, "start": 0.0, "end": 1.0, "text": "hello", "speaker": "A"}]'
    )
    mocker.patch.object(
        rf,
        "get_feature_flag_client",
        return_value=Mock(is_enabled=Mock(return_value=False)),
    )
    mocker.patch.object(rf, "correct_acronyms", side_effect=lambda text: text)
    mocker.patch.object(rf, "extract_participants", return_value=[])


def test_reads_raw_segments_and_builds_speaker_transcriptions(
    in_memory_s3: InMemoryS3, mocker: MockerFixture
) -> None:
    _setup_pipeline(in_memory_s3, mocker)

    result = rf.run_finalize_transcription(MEETING_ID)

    assert len(result) == 1
    assert result[0].meeting_id == MEETING_ID
    assert "hello" in result[0].transcription


def test_writes_full_transcript_json_to_s3(
    in_memory_s3: InMemoryS3, mocker: MockerFixture
) -> None:
    _setup_pipeline(in_memory_s3, mocker)

    result = rf.run_finalize_transcription(MEETING_ID)

    written = json.loads(in_memory_s3.objects[FULL_TRANSCRIPT_KEY])
    assert written["meeting_id"] == MEETING_ID
    assert [s["transcription"] for s in written["segments"]] == [
        r.transcription for r in result
    ]
    assert [s["speaker"] for s in written["segments"]] == [r.speaker for r in result]


def test_task_fails_when_full_transcript_write_fails(
    in_memory_s3: InMemoryS3, mocker: MockerFixture
) -> None:
    _setup_pipeline(in_memory_s3, mocker)
    write_failure = RuntimeError("S3 put failed")
    mocker.patch(
        "mcr_meeting.app.infrastructure.s3.write_full_transcript",
        side_effect=write_failure,
    )

    with pytest.raises(RuntimeError, match="S3 put failed"):
        rf.run_finalize_transcription(MEETING_ID)
