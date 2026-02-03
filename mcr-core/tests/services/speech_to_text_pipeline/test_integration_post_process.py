"""Test integration for the post process step."""

import pytest
from loguru import logger

from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    SpeakerTranscription,
)
from mcr_meeting.app.services.meeting_to_transcription_service import (
    merge_consecutive_segments_per_speaker,
)

# Note: Fixtures mock_feature_flag_client and create_audio_buffer
# are automatically imported from conftest.py in this directory


@pytest.fixture
def diarized_transcription_segments_simple() -> list[DiarizedTranscriptionSegment]:
    """Simple case with 3 consecutive segments from different speakers."""
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
    """Case with consecutive segments from same speaker to test merging."""
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


@pytest.fixture
def diarized_transcription_segments_empty():
    """Empty case to test error handling."""
    return []


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
    """Test that post-processing works normally.

    This test verifies the merge_consecutive_segments_per_speaker function:
    1. Merges consecutive segments from the same speaker
    2. Maintains speaker order
    3. Correctly concatenates transcription text

    This test runs multiple times with different combinations of:
    - Simple case with no consecutive segments from same speaker
    - Case with consecutive segments from same speaker that need merging
    """

    transcription_with_speech = request.getfixturevalue(fixture_name)
    meeting_id = 1

    ### ===== POST PROCESS FLOW ===== ###
    if not transcription_with_speech:
        logger.warning("No transcription segments found for meeting {}", meeting_id)
        raise InvalidAudioFileError(
            f"No transcription segments found for meeting {meeting_id}"
        )

    speaker_transcription_segments = [
        SpeakerTranscription(
            meeting_id=meeting_id,
            transcription_index=segment.id,
            speaker=segment.speaker if segment.speaker else f"INCONNU_{segment.id}",
            transcription=segment.text,
            start=segment.start,
            end=segment.end,
        )
        for segment in transcription_with_speech
    ]

    merged_segments = merge_consecutive_segments_per_speaker(
        speaker_transcription_segments
    )
    ### ===== END POST PROCESS FLOW ===== ###

    # Verify the result is a list
    assert isinstance(merged_segments, list)

    # Verify the result contains the expected number of segments
    assert len(merged_segments) == expected_count, (
        f"Expected {expected_count} merged segments, got {len(merged_segments)}"
    )

    # Verify all items are SpeakerTranscription objects
    for segment in merged_segments:
        assert isinstance(segment, SpeakerTranscription)

    # Verify the first speaker is correct
    assert merged_segments[0].speaker == expected_first_speaker, (
        f"Expected first speaker to be {expected_first_speaker}, "
        f"got {merged_segments[0].speaker}"
    )

    # Verify the first transcription text is correctly merged
    assert merged_segments[0].transcription == expected_merged_text, (
        f"Expected first transcription to be '{expected_merged_text}', "
        f"got '{merged_segments[0].transcription}'"
    )

    # Verify transcription_index is sequential
    for i, segment in enumerate(merged_segments):
        assert segment.transcription_index == i, (
            f"Expected transcription_index {i}, got {segment.transcription_index}"
        )

    # Verify meeting_id is preserved
    for segment in merged_segments:
        assert segment.meeting_id == meeting_id, (
            f"Expected meeting_id {meeting_id}, got {segment.meeting_id}"
        )


def test_integration_post_process_empty_segments():
    """Test that post-processing raises an error with empty segments."""

    transcription_with_speech = []
    meeting_id = 1

    with pytest.raises(InvalidAudioFileError) as exc_info:
        ### ===== POST PROCESS FLOW ===== ###
        if not transcription_with_speech:
            logger.warning("No transcription segments found for meeting {}", meeting_id)
            raise InvalidAudioFileError(
                f"No transcription segments found for meeting {meeting_id}"
            )

        speaker_transcription_segments = [
            SpeakerTranscription(
                meeting_id=meeting_id,
                transcription_index=segment.id,
                speaker=segment.speaker if segment.speaker else f"INCONNU_{segment.id}",
                transcription=segment.text,
                start=segment.start,
                end=segment.end,
            )
            for segment in transcription_with_speech
        ]

        _merged_segments = merge_consecutive_segments_per_speaker(
            speaker_transcription_segments
        )
        ### ===== END POST PROCESS FLOW ===== ###

    # Verify the exception message
    assert f"No transcription segments found for meeting {meeting_id}" in str(
        exc_info.value
    )
