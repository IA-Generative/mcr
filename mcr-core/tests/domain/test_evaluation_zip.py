import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from mcr_meeting.app.domain.evaluation_zip import (
    find_evaluation_dataset_root,
    is_zip_filename,
    validate_evaluation_zip_structure,
)
from mcr_meeting.app.exceptions.exceptions import InvalidEvaluationZipError

SUPPORTED_AUDIO_FORMATS = ["mp3", "wav"]


def _build_zip(names: list[str]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, b"content")
    return buffer.getvalue()


class TestIsZipFilename:
    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("dataset.zip", True),
            ("clean_dataset.zip", True),
            ("dataset.tar", False),
            ("dataset", False),
            ("", False),
            (None, False),
        ],
    )
    def test_is_zip_filename(self, filename: str | None, expected: bool) -> None:
        assert is_zip_filename(filename) is expected


class TestValidateEvaluationZipStructure:
    def test_valid_structure_passes(self) -> None:
        zip_bytes = _build_zip(
            ["raw_audios/audio1.mp3", "reference_transcripts/audio1.json"]
        )

        validate_evaluation_zip_structure(zip_bytes, SUPPORTED_AUDIO_FORMATS)

    def test_accepts_any_supported_audio_format(self) -> None:
        zip_bytes = _build_zip(
            ["raw_audios/audio1.wav", "reference_transcripts/audio1.json"]
        )

        validate_evaluation_zip_structure(zip_bytes, SUPPORTED_AUDIO_FORMATS)

    def test_missing_audio_dir_raises(self) -> None:
        zip_bytes = _build_zip(["reference_transcripts/audio1.json"])

        with pytest.raises(InvalidEvaluationZipError):
            validate_evaluation_zip_structure(zip_bytes, SUPPORTED_AUDIO_FORMATS)

    def test_missing_reference_dir_raises(self) -> None:
        zip_bytes = _build_zip(["raw_audios/audio1.mp3"])

        with pytest.raises(InvalidEvaluationZipError):
            validate_evaluation_zip_structure(zip_bytes, SUPPORTED_AUDIO_FORMATS)

    def test_unsupported_audio_format_raises(self) -> None:
        zip_bytes = _build_zip(
            ["raw_audios/audio1.flac", "reference_transcripts/audio1.json"]
        )

        with pytest.raises(InvalidEvaluationZipError):
            validate_evaluation_zip_structure(zip_bytes, SUPPORTED_AUDIO_FORMATS)

    def test_corrupted_zip_raises(self) -> None:
        with pytest.raises(InvalidEvaluationZipError):
            validate_evaluation_zip_structure(b"not a zip", SUPPORTED_AUDIO_FORMATS)


class TestFindEvaluationDatasetRoot:
    def test_finds_dataset_at_zip_root(self) -> None:
        root = Path("/tmp/extract")
        extracted = [
            root / "raw_audios",
            root / "raw_audios" / "a.mp3",
            root / "reference_transcripts",
            root / "reference_transcripts" / "a.json",
        ]

        assert find_evaluation_dataset_root(root, extracted) == root

    def test_finds_dataset_nested_one_level_down(self) -> None:
        root = Path("/tmp/extract")
        extracted = [
            root / "dataset",
            root / "dataset" / "raw_audios",
            root / "dataset" / "raw_audios" / "a.mp3",
            root / "dataset" / "reference_transcripts",
            root / "dataset" / "reference_transcripts" / "a.json",
        ]

        assert find_evaluation_dataset_root(root, extracted) == root / "dataset"

    def test_prefers_zip_root_over_nested_dataset(self) -> None:
        root = Path("/tmp/extract")
        extracted = [
            root / "raw_audios",
            root / "reference_transcripts",
            root / "nested",
            root / "nested" / "raw_audios",
            root / "nested" / "reference_transcripts",
        ]

        assert find_evaluation_dataset_root(root, extracted) == root

    def test_returns_none_when_one_directory_is_missing(self) -> None:
        root = Path("/tmp/extract")
        extracted = [
            root / "raw_audios",
            root / "raw_audios" / "a.mp3",
        ]

        assert find_evaluation_dataset_root(root, extracted) is None

    def test_ignores_dataset_nested_deeper_than_one_level(self) -> None:
        root = Path("/tmp/extract")
        extracted = [
            root / "a",
            root / "a" / "b",
            root / "a" / "b" / "raw_audios",
            root / "a" / "b" / "reference_transcripts",
        ]

        assert find_evaluation_dataset_root(root, extracted) is None
