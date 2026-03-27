"""Test integration for the pre_process step."""

from collections.abc import Callable
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
import soundfile as sf

from mcr_meeting.app.configs.base import AudioSettings
from mcr_meeting.app.services.feature_flag_service import FeatureFlag
from mcr_meeting.app.services.speech_to_text.speech_to_text import SpeechToTextPipeline


@pytest.mark.parametrize("feature_flag_enabled", [True, False])
@pytest.mark.parametrize("audio_format", ["mp3", "mp4", "m4a", "wav", "mov"])
@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client")
def test_integration_pre_process(
    mock_get_feature_flag_client: MagicMock,
    create_audio_buffer: Callable[[str], BytesIO],
    create_mock_feature_flag_client: Callable[[str, bool], Mock],
    feature_flag_enabled: bool,
    audio_format: str,
) -> None:
    mock_feature_flag_client = create_mock_feature_flag_client(
        FeatureFlag.AUDIO_NOISE_FILTERING, feature_flag_enabled
    )
    mock_get_feature_flag_client.return_value = mock_feature_flag_client
    audio_buffer = create_audio_buffer(audio_format)

    speech_to_text_pipeline = SpeechToTextPipeline()
    processed_bytes = speech_to_text_pipeline.pre_process(audio_buffer)

    # Verify the feature flag was checked
    mock_feature_flag_client.is_enabled.assert_called_once_with("audio_noise_filtering")

    if mock_feature_flag_client.is_enabled(FeatureFlag.AUDIO_NOISE_FILTERING):
        assert feature_flag_enabled is True
    else:
        assert feature_flag_enabled is False

    # Verify the result is a BytesIO object
    assert isinstance(processed_bytes, BytesIO)

    # Verify the result contains data
    result_data = processed_bytes.getvalue()
    assert len(result_data) > 0

    # Verify it's a valid WAV file by checking WAV header
    assert result_data[:4] == b"RIFF"
    assert result_data[8:12] == b"WAVE"

    # Verify the audio has the correct sample rate and number of channels
    audio_settings = AudioSettings()
    info = sf.info(BytesIO(result_data))
    assert info.channels == audio_settings.NB_AUDIO_CHANNELS, (
        f"Expected {audio_settings.NB_AUDIO_CHANNELS} channel(s), got {info.channels}"
    )
    assert info.samplerate == audio_settings.SAMPLE_RATE, (
        f"Expected sample rate of {audio_settings.SAMPLE_RATE} Hz, "
        f"got {info.samplerate} Hz"
    )


def test_pre_process_skips_filtering_when_audio_is_clean(
    mock_noise_detection_dependencies,
    create_audio_buffer,
):
    mocks = mock_noise_detection_dependencies
    mocks.mock_is_noisy.return_value = False
    audio_buffer = create_audio_buffer("wav")

    pipeline = SpeechToTextPipeline()
    pipeline.pre_process(audio_buffer)

    mocks.mock_is_noisy.assert_called_once()


def test_pre_process_applies_filtering_when_audio_is_noisy(
    mock_noise_detection_dependencies,
    create_audio_buffer,
):
    mocks = mock_noise_detection_dependencies
    mocks.mock_is_noisy.return_value = True
    mocks.mock_filter_noise.return_value = BytesIO(b"filtered")
    audio_buffer = create_audio_buffer("wav")

    pipeline = SpeechToTextPipeline()
    pipeline.pre_process(audio_buffer)

    mocks.mock_is_noisy.assert_called_once()
    mocks.mock_filter_noise.assert_called_once()
