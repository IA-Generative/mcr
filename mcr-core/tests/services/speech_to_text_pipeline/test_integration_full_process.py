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
            7,
            [
                "Intervenant 1",
                "Intervenant 1",
                "Intervenant 2",
                "Intervenant 2",
                "Intervenant 2",
                "Intervenant 1",
                "Intervenant 2",
            ],
        ),
        (
            "wav",
            False,
            "diarization_result_single_speaker",
            "mock_transcription_segments_normal",
            3,
            ["Intervenant 1", "Intervenant 1", "Intervenant 1"],
        ),
    ],
)
@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client")
@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.set_model")
@patch(
    "mcr_meeting.app.services.speech_to_text.speech_to_text.set_diarization_pipeline"
)
def test_integration_full_process(
    mock_set_diarization_pipeline,
    mock_set_model,
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
    mock_set_diarization_pipeline.return_value = mock_diarization_pipeline

    # Setup: Mock model.transcribe(...) inside transcribe()
    mock_model = MagicMock()
    # model.transcribe() returns (iterator, info), so we need to return an iterator
    mock_model.transcribe.side_effect = [
        (iter(segments), MagicMock())
        for segments in transcription_segments_list[: len(diarization_result)]
    ]
    mock_set_model.return_value = mock_model

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

    # verify content
    assert transcription_segments[0].id == 0
    assert transcription_segments[1].id == 0
    assert transcription_segments[1].start == 1.5
    assert transcription_segments[1].end == 3.0
    assert transcription_segments[1].text == "2nd segment"
    assert transcription_segments[1].speaker == "Intervenant 1"

    if expected_segments_count >= 7:
        assert transcription_segments[3].id == 2
        assert transcription_segments[3].start == 7.0
        assert transcription_segments[3].end == 9.0
        assert transcription_segments[3].text == "4th segment"
        assert transcription_segments[3].speaker == "Intervenant 2"

        assert transcription_segments[5].id == 3
        assert transcription_segments[5].text == "6th segment"
        assert transcription_segments[5].speaker == "Intervenant 1"

        assert transcription_segments[6].id == 3
        assert transcription_segments[6].text == "7th segment"
        assert transcription_segments[6].speaker == "Intervenant 2"


@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client")
@patch(
    "mcr_meeting.app.services.speech_to_text.speech_to_text.set_diarization_pipeline"
)
def test_integration_full_process_empty_diarization(
    mock_set_diarization_pipeline,
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
    mock_set_diarization_pipeline.return_value = mock_diarization_pipeline

    # Execute: Run the full pipeline
    audio_bytes = create_audio_buffer("wav")
    pipeline = SpeechToTextPipeline()
    transcription_segments = pipeline.run(audio_bytes)

    # Verify: Empty result
    assert isinstance(transcription_segments, list)
    assert len(transcription_segments) == 0
