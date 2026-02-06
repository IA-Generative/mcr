"""Test integration for the pre_process step."""

from io import BytesIO
from unittest.mock import patch

import pytest
import soundfile as sf

from mcr_meeting.app.configs.base import AudioSettings
from mcr_meeting.app.services.speech_to_text.speech_to_text import SpeechToTextPipeline

# Note: Fixtures mock_feature_flag_client and create_audio_buffer
# are automatically imported from conftest.py in this directory


@pytest.mark.parametrize("feature_flag_enabled", [True, False])
@pytest.mark.parametrize("audio_format", ["mp3", "mp4", "m4a", "wav", "mov"])
@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client")
def test_integration_pre_process(
    mock_get_feature_flag_client,
    create_audio_buffer,
    create_mock_feature_flag_client,
    feature_flag_enabled: bool,
    audio_format: str,
):
    """Test that pre-processing works normally on various audio formats.

    This test verifies the entire flow:
    1. Normalize audio to WAV format
    2. Conditionally apply noise filtering based on feature flag
    3. Return processed audio bytes with correct sample rate and channels

    This test runs multiple times with different combinations of:
    - feature_flag_enabled: True, False
    - audio_format: mp3, mp4, m4a, wav, mov
    """
    mock_feature_flag_client = create_mock_feature_flag_client(
        "audio_noise_filtering", enabled=feature_flag_enabled
    )
    mock_get_feature_flag_client.return_value = mock_feature_flag_client
    audio_buffer = create_audio_buffer(audio_format)

    speech_to_text_pipeline = SpeechToTextPipeline()
    processed_bytes = speech_to_text_pipeline.pre_process(audio_buffer)

    # Verify the feature flag was checked
    mock_feature_flag_client.is_enabled.assert_called_once_with("audio_noise_filtering")

    if mock_feature_flag_client.is_enabled("audio_noise_filtering"):
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
