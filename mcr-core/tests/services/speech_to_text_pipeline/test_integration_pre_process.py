"""Test integration for the pre_process step."""

from io import BytesIO

import pytest
import soundfile as sf

from mcr_meeting.app.configs.base import AudioSettings
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    filter_noise_from_audio_bytes,
    normalize_audio_bytes_to_wav_bytes,
)

# Note: Fixtures mock_feature_flag_client and create_audio_buffer
# are automatically imported from conftest.py in this directory


@pytest.mark.parametrize("feature_flag_enabled", [True, False])
@pytest.mark.parametrize("audio_format", ["mp3", "mp4", "m4a", "wav", "mov"])
def test_integration_pre_process(
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

    # Create mock feature flag client with the parametrized value
    mock_feature_flag_client = create_mock_feature_flag_client(
        "audio_noise_filtering", enabled=feature_flag_enabled
    )

    # Create audio buffer in the specified format
    audio_buffer = create_audio_buffer(audio_format)

    ### ===== HERE IS THE PRE-PROCESSING FLOW ===== ###

    # Normalize audio to WAV
    normalized_audio_bytes = normalize_audio_bytes_to_wav_bytes(audio_buffer)

    # Apply noise filtering only if feature flag is enabled
    if mock_feature_flag_client and mock_feature_flag_client.is_enabled(
        "audio_noise_filtering"
    ):
        processed_bytes = filter_noise_from_audio_bytes(normalized_audio_bytes)
        assert feature_flag_enabled is True
    else:
        processed_bytes = normalized_audio_bytes
        assert feature_flag_enabled is False

    ### ===== END OF PRE-PROCESSING FLOW ===== ###

    # Verify the feature flag was checked
    mock_feature_flag_client.is_enabled.assert_called_once_with("audio_noise_filtering")
    # assert feature_flag_client.is_enabled.call_count == 0

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
