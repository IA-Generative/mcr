from io import BytesIO
from unittest.mock import patch

import pytest

from mcr_meeting.app.exceptions.exceptions import SilentAudioError
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    compute_silence_ratio,
)


def _make_fake_wav_bytes(duration_seconds: float, sample_rate: int = 16000) -> BytesIO:
    """Create fake WAV bytes with correct size for a given duration."""
    header = b"\x00" * 44
    pcm_data = b"\x00" * int(duration_seconds * sample_rate * 1 * 2)
    return BytesIO(header + pcm_data)


class TestComputeSilenceRatio:
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service._detect_silences_absolute"
    )
    def test_fully_silent(self, mock_detect):
        wav = _make_fake_wav_bytes(10.0)
        mock_detect.return_value = [(0.0, 10.0)]
        assert compute_silence_ratio(wav) == 1.0

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service._detect_silences_absolute"
    )
    def test_no_silence(self, mock_detect):
        wav = _make_fake_wav_bytes(10.0)
        mock_detect.return_value = []
        assert compute_silence_ratio(wav) == 0.0

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service._detect_silences_absolute"
    )
    def test_partial_silence(self, mock_detect):
        wav = _make_fake_wav_bytes(10.0)
        mock_detect.return_value = [(0.0, 3.0), (7.0, 10.0)]
        ratio = compute_silence_ratio(wav)
        assert abs(ratio - 0.6) < 0.01

    def test_empty_audio(self):
        wav = BytesIO(b"\x00" * 44)  # Header only, no PCM data
        assert compute_silence_ratio(wav) == 1.0


class TestSilentAudioErrorPropagation:
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.speech_to_text_pipeline"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.fetch_audio_bytes"
    )
    def test_transcribe_meeting_propagates_silent_audio_error(
        self, mock_fetch, mock_pipeline
    ):
        """Verify that SilentAudioError propagates naturally (no try/catch to swallow it)."""
        from mcr_meeting.app.services.meeting_to_transcription_service import (
            transcribe_meeting,
        )

        mock_fetch.return_value = BytesIO(b"fake audio")
        mock_pipeline.run.side_effect = SilentAudioError(
            "Silent audio detected: audio is 98% silent (threshold: 95%)"
        )

        with pytest.raises(SilentAudioError, match="Silent audio detected"):
            transcribe_meeting(meeting_id=42)
