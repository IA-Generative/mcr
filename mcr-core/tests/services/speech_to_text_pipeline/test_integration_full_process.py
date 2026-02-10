"""Test integration of the full speech-to-text pipeline process."""

from unittest.mock import MagicMock, patch

import pytest

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.speech_to_text.speech_to_text import SpeechToTextPipeline


@pytest.mark.parametrize(
    "audio_format,feature_flag_enabled,diarization_fixture,transcription_fixture,expected_segments_count,expected_speakers",
    [
        (
            "mp3",
            True,
            "diarization_result_multiple_speakers",
            "mock_transcription_segments_normal",
            4,  # After post_process merging: chunk0(2→1) + chunk1(1) + chunk2(2→merged with chunk1) + chunk3(1) + chunk4(1) = 4
            [
                "Intervenant 1",  # Merged chunk 0
                "Intervenant 2",  # Merged chunks 1+2
                "Intervenant 1",  # Chunk 3
                "Intervenant 2",  # Chunk 4
            ],
        ),
        (
            "wav",
            False,
            "diarization_result_single_speaker",
            "mock_transcription_segments_normal",
            1,  # After post_process merging: all same speaker gets merged
            ["Intervenant 1"],
        ),
    ],
)
@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client")
@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.get_transcription_model")
@patch(
    "mcr_meeting.app.services.speech_to_text.speech_to_text.get_diarization_pipeline"
)
def test_integration_full_process(
    mock_get_diarization_pipeline,
    mock_get_transcription_model,
    mock_get_feature_flag_client,
    create_audio_buffer,
    create_mock_feature_flag_client,
    audio_format: str,
    feature_flag_enabled: bool,
    diarization_fixture: str,
    transcription_fixture: str,
    expected_segments_count: int,
    expected_speakers: list[str],
    request,
):
    """Test the full speech-to-text pipeline from raw audio to diarized transcription.

    This test verifies the complete flow:
    1. Pre-processing: Audio normalization and optional noise filtering
    2. Diarization: Speaker detection and segmentation
    3. VAD: Voice activity detection and segment merging
    4. Transcription: Speech-to-text for each audio chunk
    5. Post-processing: Speaker assignment and timestamp adjustment

    The test is parametrized to run with different:
    - Audio formats (mp3, wav, m4a)
    - Speaker configurations (single/multiple speakers)
    - Transcription segment patterns
    """
    # Setup: Get fixtures
    diarization_result = request.getfixturevalue(diarization_fixture)
    transcription_segments_list = request.getfixturevalue(transcription_fixture)

    # Setup: Create audio buffer in specified format
    audio_bytes = create_audio_buffer(audio_format)

    # Setup: Mock feature flag for noise filtering (disabled for simplicity)
    mock_feature_flag_client = create_mock_feature_flag_client(
        "audio_noise_filtering", enabled=feature_flag_enabled
    )
    mock_get_feature_flag_client.return_value = mock_feature_flag_client

    # Setup: Mock diarization_pipeline(tmp_audio_path) inside diarize()
    mock_diarization_pipeline = MagicMock()
    mock_diarization_pipeline.return_value = MagicMock(
        itertracks=lambda yield_label: [
            (MagicMock(start=seg.start, end=seg.end), None, seg.speaker)
            for seg in diarization_result
        ]
    )
    mock_get_diarization_pipeline.return_value = mock_diarization_pipeline

    # Setup: Mock model.transcribe(...) inside transcribe()
    mock_model = MagicMock()
    # model.transcribe() returns (iterator, info), so we need to return an iterator
    mock_model.transcribe.side_effect = [
        (iter(segments), MagicMock())
        for segments in transcription_segments_list[: len(diarization_result)]
    ]
    mock_get_transcription_model.return_value = mock_model

    # Execute: Run the full pipeline
    pipeline = SpeechToTextPipeline()
    transcription_segments = pipeline.run(audio_bytes)

    # Verify: Results structure
    assert isinstance(transcription_segments, list)
    assert len(transcription_segments) == expected_segments_count
    assert all(
        isinstance(seg, DiarizedTranscriptionSegment) for seg in transcription_segments
    )

    # Verify: Speaker assignments
    speakers_succession = [seg.speaker for seg in transcription_segments]
    assert speakers_succession == expected_speakers

    # Verify: Timestamps are valid
    assert transcription_segments[0].start >= 0
    assert all(seg.end > seg.start for seg in transcription_segments)

    # Verify: Segments are ordered by time
    for i in range(len(transcription_segments) - 1):
        assert transcription_segments[i].start <= transcription_segments[i + 1].start

    # Verify: All segments have non-empty text
    assert all(seg.text.strip() for seg in transcription_segments)

    # Verify: Feature flag was checked during pre-processing
    mock_feature_flag_client.is_enabled.assert_called_once_with("audio_noise_filtering")

    # verify content - after post_process merging
    if expected_segments_count == 4:  # multiple speakers scenario
        # First merged segment from chunk 0 (Intervenant 1)
        assert transcription_segments[0].id == 0
        assert transcription_segments[0].start == 0.0
        assert transcription_segments[0].speaker == "Intervenant 1"
        assert "1st segment" in transcription_segments[0].text
        assert "2nd segment" in transcription_segments[0].text

        # Second merged segment from chunks 1+2 (Intervenant 2)
        assert transcription_segments[1].speaker == "Intervenant 2"
        assert "3rd segment" in transcription_segments[1].text

        # Third segment from chunk 3 (Intervenant 1)
        assert transcription_segments[2].speaker == "Intervenant 1"
        assert "6th segment" in transcription_segments[2].text

        # Fourth segment from chunk 4 (Intervenant 2)
        assert transcription_segments[3].speaker == "Intervenant 2"
        assert "7th segment" in transcription_segments[3].text
    elif expected_segments_count == 1:  # single speaker scenario
        # All segments merged into one
        assert transcription_segments[0].id == 0
        assert transcription_segments[0].speaker == "Intervenant 1"
        assert "1st segment" in transcription_segments[0].text
        assert "2nd segment" in transcription_segments[0].text
        assert "3rd segment" in transcription_segments[0].text


@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client")
@patch(
    "mcr_meeting.app.services.speech_to_text.speech_to_text.get_diarization_pipeline"
)
def test_integration_full_process_empty_diarization(
    mock_get_diarization_pipeline,
    mock_get_feature_flag_client,
    create_audio_buffer,
    create_mock_feature_flag_client,
):
    """Test full pipeline when diarization returns no speakers.

    This test verifies that the pipeline correctly handles the edge case
    where no speakers are detected in the audio.
    """
    # Setup: Mock feature flag
    mock_feature_flag_client = create_mock_feature_flag_client(
        "audio_noise_filtering", enabled=False
    )
    mock_get_feature_flag_client.return_value = mock_feature_flag_client

    # Setup: Mock empty diarization result
    mock_diarization_pipeline = MagicMock()
    mock_diarization_pipeline.return_value = MagicMock(
        itertracks=lambda yield_label: []  # Empty diarization
    )
    mock_get_diarization_pipeline.return_value = mock_diarization_pipeline

    # Execute: Run the full pipeline
    audio_bytes = create_audio_buffer("wav")
    pipeline = SpeechToTextPipeline()
    transcription_segments = pipeline.run(audio_bytes)

    # Verify: Empty result
    assert isinstance(transcription_segments, list)
    assert len(transcription_segments) == 0
