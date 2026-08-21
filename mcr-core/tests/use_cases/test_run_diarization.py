import json
import subprocess
from io import BytesIO
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

import mcr_meeting.app.use_cases.transcription._shared.preprocess_audio as pa
import mcr_meeting.app.use_cases.transcription.run_diarization as rd
from mcr_meeting.app.configs.base import S3Settings
from mcr_meeting.app.schemas.transcription_schema import DiarizationSegment
from tests.mocks.in_memory_s3 import InMemoryS3

MEETING_ID = 123

# Keys hardcode : They are an interface between the app and the S3
PREPROCESSED_KEY = "artifacts/123/preprocessed_audio.wav"
DIARIZATION_KEY = "artifacts/123/diarization.json"

_AUDIO_FOLDER = S3Settings().S3_AUDIO_FOLDER
_DIARIZATION = [DiarizationSegment(start=0.0, end=1.0, speaker="A")]


def _patch_preprocessing(mocker: MockerFixture, wav: BytesIO) -> None:
    mocker.patch.object(rd.s3, "fetch_audio_bytes", return_value=BytesIO(b"raw"))
    mocker.patch.object(pa, "audio_bytes_to_wav_bytes", return_value=wav)
    mocker.patch.object(pa, "check_audio_has_minimum_duration")
    mocker.patch.object(pa, "check_audio_is_not_silent")


@pytest.fixture
def meeting_audio(in_memory_s3: InMemoryS3) -> bytes:
    """Seed S3 with real audio, long enough to clear preprocessing's guards."""
    audio = subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "wav",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    ).stdout
    in_memory_s3.objects[f"{_AUDIO_FOLDER}/{MEETING_ID}/chunk_001.wav"] = audio
    return audio


@pytest.fixture(autouse=True)
def _noise_filtering_disabled(mocker: MockerFixture) -> None:
    """The feature-flag service is the one collaborator we cannot run locally."""
    mocker.patch.object(
        pa,
        "get_feature_flag_client",
        return_value=Mock(is_enabled=Mock(return_value=False)),
    )


def test_writes_preprocessed_audio_and_diarization_to_s3(
    in_memory_s3: InMemoryS3, meeting_audio: bytes
) -> None:
    processor = Mock()
    processor.diarize.return_value = _DIARIZATION

    rd.run_diarization(MEETING_ID, processor)

    diarized_audio = processor.diarize.call_args.kwargs["audio_bytes"].getvalue()
    assert in_memory_s3.objects[PREPROCESSED_KEY] == diarized_audio
    assert json.loads(in_memory_s3.objects[DIARIZATION_KEY]) == [
        {"start": 0.0, "end": 1.0, "speaker": "A"}
    ]


def test_uploads_full_audio_even_after_diarization_consumed_the_buffer(
    in_memory_s3: InMemoryS3, meeting_audio: bytes
) -> None:
    processor = Mock()
    consumed: list[int] = []

    def _consume(audio_bytes: BytesIO) -> list[DiarizationSegment]:
        consumed.append(len(audio_bytes.read()))
        return _DIARIZATION

    processor.diarize.side_effect = lambda audio_bytes: _consume(audio_bytes)

    rd.run_diarization(MEETING_ID, processor)

    assert consumed == [len(in_memory_s3.objects[PREPROCESSED_KEY])]
