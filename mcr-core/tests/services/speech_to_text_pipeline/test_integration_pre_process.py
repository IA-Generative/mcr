"""Test integration for the shared preprocess_audio step."""

from io import BytesIO

import pytest
import soundfile as sf

from mcr_meeting.app.configs.base import AudioSettings
from mcr_meeting.app.exceptions.exceptions import SilentAudioError
from mcr_meeting.app.infrastructure.unleash import FeatureFlag
from mcr_meeting.app.use_cases.transcription._shared.preprocess_audio import (
    preprocess_audio,
)
from tests.mocks.in_memory_feature_flags import InMemoryFeatureFlagClient


@pytest.mark.parametrize("feature_flag_enabled", [True, False])
@pytest.mark.parametrize("audio_format", ["mp3", "mp4", "m4a", "wav", "mov"])
def test_integration_pre_process(
    create_audio_buffer,
    feature_flags: InMemoryFeatureFlagClient,
    feature_flag_enabled: bool,
    audio_format: str,
):
    if feature_flag_enabled:
        feature_flags.enable(FeatureFlag.AUDIO_NOISE_FILTERING)
    audio_buffer = create_audio_buffer(audio_format)

    processed_bytes = preprocess_audio(audio_buffer)

    assert FeatureFlag.AUDIO_NOISE_FILTERING in feature_flags.calls

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


def test_pre_process_recovers_phase_inverted_audio_when_downmix_enabled(
    create_phase_inverted_stereo_buffer,
    feature_flags: InMemoryFeatureFlagClient,
):
    feature_flags.enable(FeatureFlag.AUDIO_PHASE_AWARE_DOWNMIX)

    preprocess_audio(create_phase_inverted_stereo_buffer(3.0))


def test_pre_process_flags_phase_inverted_audio_when_downmix_disabled(
    create_phase_inverted_stereo_buffer,
    feature_flags: InMemoryFeatureFlagClient,
):
    feature_flags.disable(FeatureFlag.AUDIO_PHASE_AWARE_DOWNMIX)

    with pytest.raises(SilentAudioError):
        preprocess_audio(create_phase_inverted_stereo_buffer(3.0))
