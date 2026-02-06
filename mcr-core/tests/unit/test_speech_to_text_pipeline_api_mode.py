"""Unit tests for SpeechToTextPipeline with API mode feature flag"""

from io import BytesIO
from unittest.mock import Mock, patch

import numpy as np
import pytest

from mcr_meeting.app.services.feature_flag_service import FeatureFlag
from mcr_meeting.app.services.speech_to_text.speech_to_text import SpeechToTextPipeline


@pytest.fixture
def pipeline():
    """Create a SpeechToTextPipeline instance"""
    return SpeechToTextPipeline()


@pytest.fixture
def mock_audio_array():
    """Create mock audio numpy array"""
    return np.array([0.1, 0.2, 0.3], dtype=np.float32)


@pytest.fixture
def mock_audio_bytes():
    """Create mock audio bytes"""
    return BytesIO(b"fake_audio_data")


@pytest.fixture
def mock_feature_flag_disabled():
    """Mock feature flag client returning disabled"""
    mock_client = Mock()
    mock_client.is_enabled.return_value = False
    return mock_client


@pytest.fixture
def mock_feature_flag_enabled():
    """Mock feature flag client returning enabled"""
    mock_client = Mock()
    mock_client.is_enabled.return_value = True
    return mock_client


def test_transcribe_uses_local_when_flag_disabled(
    pipeline, mock_audio_array, mock_feature_flag_disabled
):
    """Test that transcribe() uses local implementation when flag is disabled"""
    with (
        patch(
            "mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client",
            return_value=mock_feature_flag_disabled,
        ),
        patch.object(pipeline, "_transcribe_local", return_value=[]) as mock_local,
        patch.object(pipeline, "_transcribe_api", return_value=[]) as mock_api,
    ):
        from mcr_meeting.app.configs.base import WhisperTranscriptionSettings

        settings = WhisperTranscriptionSettings()
        pipeline.transcribe(mock_audio_array, settings)

        # Assert local was called, API was not
        mock_local.assert_called_once()
        mock_api.assert_not_called()
        mock_feature_flag_disabled.is_enabled.assert_called_with(
            FeatureFlag.API_BASED_TRANSCRIPTION
        )


def test_transcribe_uses_api_when_flag_enabled(
    pipeline, mock_audio_array, mock_feature_flag_enabled
):
    """Test that transcribe() uses API implementation when flag is enabled"""
    with (
        patch(
            "mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client",
            return_value=mock_feature_flag_enabled,
        ),
        patch.object(pipeline, "_transcribe_local", return_value=[]) as mock_local,
        patch.object(pipeline, "_transcribe_api", return_value=[]) as mock_api,
    ):
        from mcr_meeting.app.configs.base import WhisperTranscriptionSettings

        settings = WhisperTranscriptionSettings()
        pipeline.transcribe(mock_audio_array, settings)

        # Assert API was called, local was not
        mock_api.assert_called_once()
        mock_local.assert_not_called()
        mock_feature_flag_enabled.is_enabled.assert_called_with(
            FeatureFlag.API_BASED_TRANSCRIPTION
        )


def test_diarize_uses_local_when_flag_disabled(
    pipeline, mock_audio_bytes, mock_feature_flag_disabled
):
    """Test that diarize() uses local implementation when flag is disabled"""
    with (
        patch(
            "mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client",
            return_value=mock_feature_flag_disabled,
        ),
        patch.object(pipeline, "_diarize_local", return_value=[]) as mock_local,
        patch.object(pipeline, "_diarize_api", return_value=[]) as mock_api,
    ):
        pipeline.diarize(mock_audio_bytes)

        # Assert local was called, API was not
        mock_local.assert_called_once_with(mock_audio_bytes)
        mock_api.assert_not_called()
        mock_feature_flag_disabled.is_enabled.assert_called_with(
            FeatureFlag.API_BASED_DIARIZATION
        )


def test_diarize_uses_api_when_flag_enabled(
    pipeline, mock_audio_bytes, mock_feature_flag_enabled
):
    """Test that diarize() uses API implementation when flag is enabled"""
    with (
        patch(
            "mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client",
            return_value=mock_feature_flag_enabled,
        ),
        patch.object(pipeline, "_diarize_local", return_value=[]) as mock_local,
        patch.object(pipeline, "_diarize_api", return_value=[]) as mock_api,
    ):
        pipeline.diarize(mock_audio_bytes)

        # Assert API was called, local was not
        mock_api.assert_called_once_with(mock_audio_bytes)
        mock_local.assert_not_called()
        mock_feature_flag_enabled.is_enabled.assert_called_with(
            FeatureFlag.API_BASED_DIARIZATION
        )


def test_transcribe_api_calls_openai_client(pipeline, mock_audio_array):
    """Test that _transcribe_api calls OpenAI client correctly"""
    mock_settings = Mock()
    mock_settings.TRANSCRIPTION_API_MODEL = "whisper-1"
    mock_settings.API_LANGUAGE = "fr"
    mock_settings.TRANSCRIPTION_API_KEY = "test-key"
    mock_settings.TRANSCRIPTION_API_BASE_URL = "https://api.example.com"

    mock_response = Mock()
    mock_response.segments = [{"start": 0.0, "end": 5.0, "text": "Test transcription"}]

    mock_client = Mock()
    mock_client.audio.transcriptions.create.return_value = mock_response

    mock_sf = Mock()
    mock_sf.write.return_value = None

    with (
        patch.object(pipeline, "_get_api_settings", return_value=mock_settings),
        patch.object(pipeline, "_get_openai_client", return_value=mock_client),
        patch(
            "soundfile.write",
            side_effect=lambda buf, *args, **kwargs: buf.write(b"fake_wav_data"),
        ),
    ):
        from mcr_meeting.app.configs.base import WhisperTranscriptionSettings

        settings = WhisperTranscriptionSettings()
        result = pipeline._transcribe_api(mock_audio_array, settings)

        # Assert API was called
        mock_client.audio.transcriptions.create.assert_called_once()
        assert len(result) == 1
        assert result[0].text == "Test transcription"


def test_diarize_api_calls_http_client(pipeline, mock_audio_bytes):
    """Test that _diarize_api calls HTTP client correctly"""
    mock_settings = Mock()
    mock_settings.DIARIZATION_API_BASE_URL = "https://diarization.example.com"
    mock_settings.DIARIZATION_API_KEY = "test-key"

    mock_response = Mock()
    mock_response.json.return_value = {
        "segments": [{"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"}]
    }

    mock_client = Mock()
    mock_client.post.return_value = mock_response

    with (
        patch.object(pipeline, "_get_api_settings", return_value=mock_settings),
        patch.object(pipeline, "_get_http_client", return_value=mock_client),
    ):
        result = pipeline._diarize_api(mock_audio_bytes)

        # Assert API was called
        mock_client.post.assert_called_once()
        assert len(result) == 1
        assert result[0].speaker == "LOCUTEUR_00"  # Converted to French
