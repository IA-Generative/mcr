"""Test integration of the shared transcribe_diarized_audio step."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from mcr_meeting.app.configs.base import WhisperTranscriptionSettings
from mcr_meeting.app.infrastructure import speech_to_text_models
from mcr_meeting.app.infrastructure.diarization import DiarizationProcessor
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationSegment,
    DiarizedTranscriptionSegment,
    TranscriptionSegment,
)
from mcr_meeting.app.use_cases.transcription._shared.transcribe_diarized_audio import (
    transcribe_diarized_audio,
)

transcription_settings = WhisperTranscriptionSettings()
M = transcription_settings.MAX_CHUNK_DURATION

_DIARIZATION_PIPELINE = (
    "mcr_meeting.app.infrastructure.speech_to_text_models.get_diarization_pipeline"
)
_TRANSCRIPTION_MODEL = (
    "mcr_meeting.app.infrastructure.speech_to_text_models.get_transcription_model"
)


def run_the_code_to_test(
    pre_processed_audio_bytes: BytesIO,
) -> list[DiarizedTranscriptionSegment]:
    diarization_result = DiarizationProcessor(
        speech_to_text_models.get_diarization_pipeline
    ).diarize(audio_bytes=pre_processed_audio_bytes)

    if not diarization_result:
        return []

    return transcribe_diarized_audio(
        pre_processed_audio_bytes,
        diarization_result,
        TranscriptionProcessor(speech_to_text_models.get_transcription_model),
    )


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
@patch("mcr_meeting.app.infrastructure.diarization.get_feature_flag_client")
@patch("mcr_meeting.app.infrastructure.transcription.get_feature_flag_client")
@patch(_TRANSCRIPTION_MODEL)
@patch(_DIARIZATION_PIPELINE)
def test_integration_center_process_normal_flow(
    mock_get_diarization_pipeline: MagicMock,
    mock_get_transcription_model: MagicMock,
    mock_get_feature_flag_client_transcription: MagicMock,
    mock_get_feature_flag_client_diarization: MagicMock,
    diarization_fixture: str,
    transcription_fixture: str,
    expected_segments_count: int,
    expected_speakers: list[str],
    pre_processed_audio_bytes: BytesIO,
    create_mock_feature_flag_client,
    request: pytest.FixtureRequest,
) -> None:
    diarization_result = request.getfixturevalue(diarization_fixture)
    transcription_segments_list = request.getfixturevalue(transcription_fixture)

    mock_get_feature_flag_client_diarization.return_value = (
        create_mock_feature_flag_client("api_based_diarization", enabled=False)
    )
    mock_get_feature_flag_client_transcription.return_value = (
        create_mock_feature_flag_client("api_based_transcription", enabled=False)
    )

    mock_diarization_pipeline = MagicMock()
    mock_diarization_pipeline.return_value = MagicMock(
        itertracks=lambda yield_label: [
            (MagicMock(start=seg.start, end=seg.end), None, seg.speaker)
            for seg in diarization_result
        ]
    )
    mock_get_diarization_pipeline.return_value = mock_diarization_pipeline

    mock_model = MagicMock()
    mock_model.transcribe.side_effect = [
        (iter(segments), MagicMock()) for segments in transcription_segments_list
    ]
    mock_get_transcription_model.return_value = mock_model

    transcription_segments = run_the_code_to_test(pre_processed_audio_bytes)

    assert len(transcription_segments) == expected_segments_count
    assert all(
        isinstance(seg, DiarizedTranscriptionSegment) for seg in transcription_segments
    )

    speakers_succession = [seg.speaker for seg in transcription_segments]
    assert speakers_succession == expected_speakers

    assert all(seg.start >= 0 for seg in transcription_segments)
    assert all(seg.end > seg.start for seg in transcription_segments)

    assert transcription_segments[0].id == 0
    assert transcription_segments[1].id == 0
    assert transcription_segments[1].start == 1.51
    assert transcription_segments[1].end == 3.0
    assert transcription_segments[1].text == "2nd segment"
    assert transcription_segments[1].speaker == "Intervenant 1"

    if expected_segments_count >= 7:
        assert transcription_segments[3].id == 2
        assert transcription_segments[3].start == 2 * M
        assert transcription_segments[3].end == 2 * M + 2.0
        assert transcription_segments[3].text == "4th segment"
        assert transcription_segments[3].speaker == "Intervenant 2"

        assert transcription_segments[5].id == 3
        assert transcription_segments[5].text == "6th segment"
        assert transcription_segments[5].speaker == "Intervenant 1"

        assert transcription_segments[6].id == 3
        assert transcription_segments[6].text == "7th segment"
        assert transcription_segments[6].speaker == "Intervenant 2"


@patch("mcr_meeting.app.infrastructure.diarization.get_feature_flag_client")
@patch(_DIARIZATION_PIPELINE)
def test_integration_center_process_empty_diarization(
    mock_get_diarization_pipeline: MagicMock,
    mock_get_feature_flag_client_diarization: MagicMock,
    pre_processed_audio_bytes: BytesIO,
    create_mock_feature_flag_client,
) -> None:
    mock_get_feature_flag_client_diarization.return_value = (
        create_mock_feature_flag_client("api_based_diarization", enabled=False)
    )

    mock_diarization_pipeline = MagicMock()
    mock_diarization_pipeline.return_value = MagicMock(
        itertracks=lambda yield_label: []
    )
    mock_get_diarization_pipeline.return_value = mock_diarization_pipeline

    transcription_segments = run_the_code_to_test(pre_processed_audio_bytes)

    assert len(transcription_segments) == 0


@patch("mcr_meeting.app.infrastructure.diarization.get_feature_flag_client")
@patch("mcr_meeting.app.infrastructure.transcription.get_feature_flag_client")
@patch(_TRANSCRIPTION_MODEL)
@patch(_DIARIZATION_PIPELINE)
def test_integration_center_process_with_empty_chunks(
    mock_get_diarization_pipeline: MagicMock,
    mock_get_transcription_model: MagicMock,
    mock_get_feature_flag_client_transcription: MagicMock,
    mock_get_feature_flag_client_diarization: MagicMock,
    diarization_result_multiple_speakers: list[DiarizationSegment],
    mock_transcription_segments_with_empty: list[list[TranscriptionSegment]],
    pre_processed_audio_bytes: BytesIO,
    create_mock_feature_flag_client,
) -> None:
    diarization_result = diarization_result_multiple_speakers

    mock_get_feature_flag_client_diarization.return_value = (
        create_mock_feature_flag_client("api_based_diarization", enabled=False)
    )
    mock_get_feature_flag_client_transcription.return_value = (
        create_mock_feature_flag_client("api_based_transcription", enabled=False)
    )

    mock_diarization_pipeline = MagicMock()
    mock_diarization_pipeline.return_value = MagicMock(
        itertracks=lambda yield_label: [
            (MagicMock(start=seg.start, end=seg.end), None, seg.speaker)
            for seg in diarization_result
        ]
    )
    mock_get_diarization_pipeline.return_value = mock_diarization_pipeline

    mock_model = MagicMock()
    mock_model.transcribe.side_effect = [
        (iter(segments), MagicMock())
        for segments in mock_transcription_segments_with_empty
    ]
    mock_get_transcription_model.return_value = mock_model

    transcription_segments = run_the_code_to_test(pre_processed_audio_bytes)

    assert len(transcription_segments) == 2
    assert transcription_segments[0].text == "1st segment"
    assert transcription_segments[1].text == "3rd segment"
