import json
from io import BytesIO
from unittest.mock import Mock

from pytest_mock import MockerFixture

import mcr_meeting.app.use_cases.transcription._shared.preprocess_audio as pa
import mcr_meeting.app.use_cases.transcription.run_diarization as rd
from mcr_meeting.app.schemas.transcription_schema import DiarizationSegment
from tests.mocks.in_memory_s3 import InMemoryS3

MEETING_ID = 123

# Clés écrites en dur : elles font partie du contrat d'interface de l'app
# vers S3, un changement ici casse la reprise des pipelines en vol.
PREPROCESSED_KEY = "artifacts/123/preprocessed_audio.wav"
DIARIZATION_KEY = "artifacts/123/diarization.json"

_DIARIZATION = [DiarizationSegment(start=0.0, end=1.0, speaker="A")]


def _patch_preprocessing(mocker: MockerFixture, wav: BytesIO) -> None:
    mocker.patch.object(
        pa,
        "get_feature_flag_client",
        return_value=Mock(is_enabled=Mock(return_value=False)),
    )
    mocker.patch.object(rd.s3, "fetch_audio_bytes", return_value=BytesIO(b"raw"))
    mocker.patch.object(pa, "audio_bytes_to_wav_bytes", return_value=wav)
    mocker.patch.object(pa, "check_audio_is_not_silent")


def test_writes_preprocessed_audio_and_diarization_to_s3(
    in_memory_s3: InMemoryS3, mocker: MockerFixture
) -> None:
    wav = BytesIO(b"wav-data")
    _patch_preprocessing(mocker, wav)
    processor = Mock()
    processor.diarize.return_value = _DIARIZATION

    rd.run_diarization(MEETING_ID, processor)

    processor.diarize.assert_called_once_with(audio_bytes=wav)
    assert in_memory_s3.objects[PREPROCESSED_KEY] == b"wav-data"
    assert json.loads(in_memory_s3.objects[DIARIZATION_KEY]) == [
        {"start": 0.0, "end": 1.0, "speaker": "A"}
    ]


def test_uploads_full_audio_even_after_diarization_consumed_the_buffer(
    in_memory_s3: InMemoryS3, mocker: MockerFixture
) -> None:
    wav = BytesIO(b"wav-data")
    _patch_preprocessing(mocker, wav)
    processor = Mock()

    def _consume(audio_bytes: BytesIO) -> list[DiarizationSegment]:
        audio_bytes.read()
        return _DIARIZATION

    processor.diarize.side_effect = lambda audio_bytes: _consume(audio_bytes)

    rd.run_diarization(MEETING_ID, processor)

    assert in_memory_s3.objects[PREPROCESSED_KEY] == b"wav-data"
