"""Test integration for the shared post_process_segments step."""

from unittest.mock import MagicMock

import pytest

from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
)
from mcr_meeting.app.use_cases.transcription._shared.post_process_segments import (
    post_process_segments,
)


@pytest.fixture(autouse=True)
def mock_post_process_external_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    feature_flag_client = MagicMock()
    feature_flag_client.is_enabled.return_value = True

    monkeypatch.setattr(
        "mcr_meeting.app.use_cases.transcription._shared.post_process_segments.get_feature_flag_client",
        lambda: feature_flag_client,
    )
    monkeypatch.setattr(
        "mcr_meeting.app.use_cases.transcription._shared.post_process_segments._apply_text_correction",
        lambda segments, correct_chunk: segments,
    )


@pytest.fixture
def diarized_transcription_segments_simple() -> list[DiarizedTranscriptionSegment]:
    return [
        DiarizedTranscriptionSegment(
            id=0,
            speaker="SPEAKER_00",
            text="Hello everyone.",
            start=0.0,
            end=2.0,
        ),
        DiarizedTranscriptionSegment(
            id=1,
            speaker="SPEAKER_01",
            text="Hi there.",
            start=2.0,
            end=3.5,
        ),
        DiarizedTranscriptionSegment(
            id=2,
            speaker="SPEAKER_00",
            text="How are you?",
            start=3.5,
            end=5.0,
        ),
    ]


@pytest.fixture
def diarized_transcription_segments_consecutive():
    return [
        DiarizedTranscriptionSegment(
            id=0,
            speaker="SPEAKER_00",
            text="Hello",
            start=0.0,
            end=1.0,
        ),
        DiarizedTranscriptionSegment(
            id=1,
            speaker="SPEAKER_00",
            text="everyone.",
            start=1.0,
            end=2.0,
        ),
        DiarizedTranscriptionSegment(
            id=2,
            speaker="SPEAKER_01",
            text="Hi",
            start=2.0,
            end=2.5,
        ),
        DiarizedTranscriptionSegment(
            id=3,
            speaker="SPEAKER_01",
            text="there.",
            start=2.5,
            end=3.5,
        ),
    ]


@pytest.mark.parametrize(
    "fixture_name,expected_count,expected_first_speaker,expected_merged_text",
    [
        ("diarized_transcription_segments_simple", 3, "SPEAKER_00", "Hello everyone."),
        (
            "diarized_transcription_segments_consecutive",
            2,
            "SPEAKER_00",
            "Hello everyone.",
        ),
    ],
)
def test_integration_post_process(
    fixture_name: str,
    expected_count: int,
    expected_first_speaker: str,
    expected_merged_text: str,
    request,
):
    transcription_with_speech = request.getfixturevalue(fixture_name)

    merged_segments = post_process_segments(transcription_with_speech)

    assert isinstance(merged_segments, list)

    assert len(merged_segments) == expected_count, (
        f"Expected {expected_count} merged segments, got {len(merged_segments)}"
    )

    for segment in merged_segments:
        assert isinstance(segment, DiarizedTranscriptionSegment)

    assert merged_segments[0].speaker == expected_first_speaker, (
        f"Expected first speaker to be {expected_first_speaker}, "
        f"got {merged_segments[0].speaker}"
    )

    assert merged_segments[0].text == expected_merged_text, (
        f"Expected first transcription to be '{expected_merged_text}', "
        f"got '{merged_segments[0].text}'"
    )

    for i, segment in enumerate(merged_segments):
        assert segment.id == i, f"Expected transcription_index {i}, got {segment.id}"
