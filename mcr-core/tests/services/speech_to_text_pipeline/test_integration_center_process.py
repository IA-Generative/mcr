"""Test integration of the speech-to-text pipeline center process."""

from io import BytesIO
from typing import List
from unittest.mock import MagicMock, patch

import pytest
from loguru import logger

from mcr_meeting.app.configs.base import WhisperTranscriptionSettings
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
)
from mcr_meeting.app.services.speech_to_text.speech_to_text import SpeechToTextPipeline
from mcr_meeting.app.services.speech_to_text.types import (
    DiarizationSegment,
)
from mcr_meeting.app.services.speech_to_text.utils import (
    diarize_vad_transcription_segments,
    get_vad_segments_from_diarization,
)

transcription_settings = WhisperTranscriptionSettings()


def run_the_code_to_test(
    pipeline: SpeechToTextPipeline,
    pre_processed_audio_bytes: BytesIO,
) -> List[DiarizedTranscriptionSegment]:
    """Execute the center process flow that we want to test.

    This function contains the exact code from SpeechToTextPipeline.run() that
    processes diarization results and transcribes audio chunks.

    Args:
        pipeline: SpeechToTextPipeline instance to use for diarize() and transcribe()
        pre_processed_audio_bytes: Pre-processed audio bytes

    Returns:
        List of diarized transcription segments with speaker assignments
    """
    ### ===== CENTER PROCESS FLOW ===== ###
    diarization_result = pipeline.diarize(
        pre_processed_audio_bytes,
    )

    if not diarization_result:
        logger.info("No diarization result. Returning empty transcription.")
        return []

    vad_spans: List[DiarizationSegment] = get_vad_segments_from_diarization(
        diarization_result
    )

    vad_transcription_segments = pipeline.transcribe_audio(
        pre_processed_audio_bytes, vad_spans
    )

    transcription_segments = diarize_vad_transcription_segments(
        vad_transcription_segments, diarization_result
    )
    ### ===== END CENTER PROCESS FLOW ===== ###

    return transcription_segments


# Note: Fixtures diarization_result_multiple_speakers, diarization_result_single_speaker,
# diarization_result_empty, pre_processed_audio_bytes, mock_transcription_segments_normal,
# and mock_transcription_segments_with_empty are automatically imported from conftest.py


@pytest.mark.parametrize(
    "diarization_fixture,transcription_fixture,expected_segments_count,expected_speakers",
    [
        (
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
            "diarization_result_single_speaker",
            "mock_transcription_segments_normal",
            3,
            ["Intervenant 1", "Intervenant 1", "Intervenant 1"],
        ),
    ],
)
@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.set_model")
@patch(
    "mcr_meeting.app.services.speech_to_text.speech_to_text.set_diarization_pipeline"
)
def test_integration_center_process_normal_flow(
    mock_set_diarization_pipeline,
    mock_set_model,
    diarization_fixture: str,
    transcription_fixture: str,
    expected_segments_count: int,
    expected_speakers: list[str],
    pre_processed_audio_bytes,
    request,
):
    """Test center process with normal flow and different speaker configurations.

    This test verifies:
    1. VAD segments extraction from diarization
    2. Audio splitting on timestamps
    3. Transcription of each chunk
    4. Timestamp adjustment relative to original audio
    5. Speaker assignment to transcription segments
    """
    diarization_result = request.getfixturevalue(diarization_fixture)
    transcription_segments_list = request.getfixturevalue(transcription_fixture)

    # Mock diarization_pipeline(tmp_audio_path) inside diarize()
    mock_diarization_pipeline = MagicMock()
    mock_diarization_pipeline.return_value = MagicMock(
        itertracks=lambda yield_label: [
            (MagicMock(start=seg.start, end=seg.end), None, seg.speaker)
            for seg in diarization_result
        ]
    )
    mock_set_diarization_pipeline.return_value = mock_diarization_pipeline

    # Mock model.transcribe(...) inside transcribe()
    mock_model = MagicMock()
    # model.transcribe() returns (iterator, info), so we need to return an iterator
    mock_model.transcribe.side_effect = [
        (iter(segments), MagicMock())
        for segments in transcription_segments_list[: len(diarization_result)]
    ]
    mock_set_model.return_value = mock_model

    # Create pipeline instance
    pipeline = SpeechToTextPipeline()

    # Run the code to test
    transcription_segments = run_the_code_to_test(pipeline, pre_processed_audio_bytes)

    # Verify results
    assert len(transcription_segments) == expected_segments_count
    assert all(
        isinstance(seg, DiarizedTranscriptionSegment) for seg in transcription_segments
    )
    assert all(hasattr(seg, "speaker") for seg in transcription_segments)

    # Verify speakers are from expected list
    speakers_succession = [seg.speaker for seg in transcription_segments]
    assert speakers_succession == expected_speakers

    # Verify timestamps are adjusted correctly
    assert all(seg.start >= 0 for seg in transcription_segments)
    assert all(seg.end > seg.start for seg in transcription_segments)

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


@patch(
    "mcr_meeting.app.services.speech_to_text.speech_to_text.set_diarization_pipeline"
)
def test_integration_center_process_empty_diarization(
    mock_set_diarization_pipeline,
    pre_processed_audio_bytes,
):
    """Test center process when diarization returns empty result.

    This test verifies that the flow correctly handles empty diarization
    and returns an empty list of transcription segments.
    """
    # Mock diarization_pipeline(tmp_audio_path) to return empty result
    mock_diarization_pipeline = MagicMock()
    mock_diarization_pipeline.return_value = MagicMock(
        itertracks=lambda yield_label: []  # Empty diarization
    )
    mock_set_diarization_pipeline.return_value = mock_diarization_pipeline

    # Create pipeline instance
    pipeline = SpeechToTextPipeline()

    # Run the code to test
    transcription_segments = run_the_code_to_test(pipeline, pre_processed_audio_bytes)

    # Verify empty result
    assert len(transcription_segments) == 0


@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.set_model")
@patch(
    "mcr_meeting.app.services.speech_to_text.speech_to_text.set_diarization_pipeline"
)
def test_integration_center_process_with_empty_chunks(
    mock_set_diarization_pipeline,
    mock_set_model,
    diarization_result_multiple_speakers,
    mock_transcription_segments_with_empty,
    pre_processed_audio_bytes,
):
    """Test center process when some chunks produce no transcription.

    This test verifies that the flow correctly handles empty transcription
    chunks by skipping them (continue statement).
    """
    diarization_result = diarization_result_multiple_speakers

    # Mock diarization_pipeline(tmp_audio_path) inside diarize()
    mock_diarization_pipeline = MagicMock()
    mock_diarization_pipeline.return_value = MagicMock(
        itertracks=lambda yield_label: [
            (MagicMock(start=seg.start, end=seg.end), None, seg.speaker)
            for seg in diarization_result
        ]
    )
    mock_set_diarization_pipeline.return_value = mock_diarization_pipeline

    # Mock model.transcribe(...) to return empty list for middle chunk
    mock_model = MagicMock()
    # With gaps in diarization, we have 4 VAD chunks (last 2 diarization segments merged): need mock responses for each
    mock_model.transcribe.side_effect = [
        (iter(segments), MagicMock())
        for segments in mock_transcription_segments_with_empty
    ]
    mock_set_model.return_value = mock_model

    # Create pipeline instance
    pipeline = SpeechToTextPipeline()

    # Run the code to test
    transcription_segments = run_the_code_to_test(pipeline, pre_processed_audio_bytes)

    # Verify only non-empty chunks were processed (first and third chunks)
    assert len(transcription_segments) == 2
    assert transcription_segments[0].text == "1st segment"
    assert transcription_segments[1].text == "3rd segment"
