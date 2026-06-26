"""Test integration for the pre_process step."""

from io import BytesIO
from unittest.mock import patch

import pytest
import soundfile as sf

from mcr_meeting.app.configs.base import AudioSettings
from mcr_meeting.app.exceptions.exceptions import SilentAudioError
from mcr_meeting.app.infrastructure.unleash import FeatureFlag
from mcr_meeting.app.services.speech_to_text.speech_to_text import SpeechToTextPipeline


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
    mock_feature_flag_client = create_mock_feature_flag_client(
        FeatureFlag.AUDIO_NOISE_FILTERING, enabled=feature_flag_enabled
    )
    mock_get_feature_flag_client.return_value = mock_feature_flag_client
    audio_buffer = create_audio_buffer(audio_format)

    speech_to_text_pipeline = SpeechToTextPipeline()
    processed_bytes = speech_to_text_pipeline.pre_process(audio_buffer)

    # Verify the feature flag was checked (pre_process also checks the downmix flag)
    mock_feature_flag_client.is_enabled.assert_any_call("audio_noise_filtering")

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


@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client")
def test_pre_process_recovers_phase_inverted_audio_when_downmix_enabled(
    mock_get_feature_flag_client,
    create_phase_inverted_stereo_buffer,
    create_mock_feature_flag_client,
):
    """With the phase-aware downmix flag on, inverted-stereo input is not flagged silent."""
    mock_get_feature_flag_client.return_value = create_mock_feature_flag_client(
        FeatureFlag.AUDIO_PHASE_AWARE_DOWNMIX, enabled=True
    )

    pipeline = SpeechToTextPipeline()
    pipeline.pre_process(create_phase_inverted_stereo_buffer(3.0))  # Should not raise


@patch("mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client")
def test_pre_process_flags_phase_inverted_audio_when_downmix_disabled(
    mock_get_feature_flag_client,
    create_phase_inverted_stereo_buffer,
    create_mock_feature_flag_client,
):
    """Without the flag, the cancelling downmix still trips the silence check."""
    mock_get_feature_flag_client.return_value = create_mock_feature_flag_client(
        FeatureFlag.AUDIO_NOISE_FILTERING, enabled=False
    )

    pipeline = SpeechToTextPipeline()
    with pytest.raises(SilentAudioError):
        pipeline.pre_process(create_phase_inverted_stereo_buffer(3.0))
