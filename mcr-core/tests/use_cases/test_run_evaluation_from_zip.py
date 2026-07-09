import zipfile
from io import BytesIO
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

import mcr_meeting.app.use_cases.run_evaluation_from_zip as ruez

_REFERENCE_JSON = (
    b'{"segments": [{"id": 0, "start": 0.0, "end": 1.0, '
    b'"text": "bonjour", "speaker": "A"}]}'
)


def _build_zip(entries: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_pairs_audios_with_references_and_runs_the_evaluation(
    mocker: MockerFixture,
) -> None:
    pipeline_cls = mocker.patch.object(ruez, "ASREvaluationPipeline")
    transcribe_audio = Mock()
    zip_data = _build_zip(
        {
            "dataset/raw_audios/a.wav": b"fake-audio",
            "dataset/reference_transcripts/a.json": _REFERENCE_JSON,
        }
    )

    ruez.run_evaluation_from_zip(zip_data, transcribe_audio)

    inputs = pipeline_cls.call_args.kwargs["inputs"]
    assert [item.uid for item in inputs] == ["a"]
    assert pipeline_cls.call_args.kwargs["transcribe_audio"] is transcribe_audio
    pipeline_cls.return_value.run_evaluation.assert_called_once()


def test_raises_when_dataset_directories_are_missing(mocker: MockerFixture) -> None:
    mocker.patch.object(ruez, "ASREvaluationPipeline")
    zip_data = _build_zip({"random/file.txt": b"content"})

    with pytest.raises(ValueError, match="must contain"):
        ruez.run_evaluation_from_zip(zip_data, Mock())


def test_raises_when_no_audio_has_a_matching_reference(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(ruez, "ASREvaluationPipeline")
    zip_data = _build_zip(
        {
            "raw_audios/a.wav": b"fake-audio",
            "reference_transcripts/other.json": _REFERENCE_JSON,
        }
    )

    with pytest.raises(ValueError, match="No valid evaluation inputs"):
        ruez.run_evaluation_from_zip(zip_data, Mock())
