"""Test integration for the shared preprocess_audio step."""

from io import BytesIO
from unittest.mock import patch

import pytest
import soundfile as sf

from mcr_meeting.app.configs.base import AudioSettings
from mcr_meeting.app.exceptions.exceptions import SilentAudioError
from mcr_meeting.app.infrastructure.unleash import FeatureFlag
from mcr_meeting.app.use_cases.transcription._shared.preprocess_audio import (
    preprocess_audio,
)

_PREPROCESS_FF = (
    "mcr_meeting.app.use_cases.transcription."
    "_shared.preprocess_audio.get_feature_flag_client"
)


@pytest.mark.parametrize("feature_flag_enabled", [True, False])
@pytest.mark.parametrize("audio_format", ["mp3", "mp4", "m4a", "wav", "mov"])
@patch(_PREPROCESS_FF)
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

    processed_bytes = preprocess_audio(audio_buffer)

    mock_feature_flag_client.is_enabled.assert_any_call("audio_noise_filtering")

    assert isinstance(processed_bytes, BytesIO)

    result_data = processed_bytes.getvalue()
    assert len(result_data) > 0

    assert result_data[:4] == b"RIFF"
    assert result_data[8:12] == b"WAVE"

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

    preprocess_audio(audio_buffer)

    mocks.mock_is_noisy.assert_called_once()


def test_pre_process_applies_filtering_when_audio_is_noisy(
    mock_noise_detection_dependencies,
    create_audio_buffer,
):
    mocks = mock_noise_detection_dependencies
    mocks.mock_is_noisy.return_value = True
    mocks.mock_filter_noise.return_value = BytesIO(b"filtered")
    audio_buffer = create_audio_buffer("wav")

    preprocess_audio(audio_buffer)

    mocks.mock_is_noisy.assert_called_once()
    mocks.mock_filter_noise.assert_called_once()


@patch(_PREPROCESS_FF)
def test_pre_process_recovers_phase_inverted_audio_when_downmix_enabled(
    mock_get_feature_flag_client,
    create_phase_inverted_stereo_buffer,
    create_mock_feature_flag_client,
):
    mock_get_feature_flag_client.return_value = create_mock_feature_flag_client(
        FeatureFlag.AUDIO_PHASE_AWARE_DOWNMIX, enabled=True
    )

    preprocess_audio(create_phase_inverted_stereo_buffer(3.0))


@patch(_PREPROCESS_FF)
def test_pre_process_flags_phase_inverted_audio_when_downmix_disabled(
    mock_get_feature_flag_client,
    create_phase_inverted_stereo_buffer,
    create_mock_feature_flag_client,
):
    mock_get_feature_flag_client.return_value = create_mock_feature_flag_client(
        FeatureFlag.AUDIO_NOISE_FILTERING, enabled=False
    )

    with pytest.raises(SilentAudioError):
        preprocess_audio(create_phase_inverted_stereo_buffer(3.0))
