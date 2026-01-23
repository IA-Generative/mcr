from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    assemble_normalized_wav_from_s3_chunks,
)


class TestAssembleNormalizedWavFromS3Chunks:
    """Tests pour la fonction assemble_normalized_wav_from_s3_chunks."""

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_bytes_to_wav_bytes"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_raise_invalid_audio_file_error_when_download_fails(
        self, mock_download: Mock, mock_normalize: Mock
    ) -> None:
        """Test que la fonction gère les échecs de téléchargement."""
        mock_download.side_effect = InvalidAudioFileError(
            "No audio chunks found to process"
        )

        empty_chunk_list = [Mock()]

        with pytest.raises(
            InvalidAudioFileError, match="No audio chunks found to process"
        ):
            assemble_normalized_wav_from_s3_chunks(iter(empty_chunk_list))

        mock_normalize.assert_not_called()

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.filter_noise_from_audio_bytes"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_bytes_to_wav_bytes"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_return_normalized_audio_bytes_when_successful_with_filtering(
        self, mock_download: Mock, mock_normalize: Mock, mock_filter: Mock
    ) -> None:
        """Test le succès de l'assemblage avec filtrage activé."""

        mock_download.return_value = BytesIO(b"raw_audio")
        normalized_audio = BytesIO(b"normalized_audio")
        mock_normalize.return_value = normalized_audio
        expected_audio_bytes = BytesIO(b"filtered_audio")
        mock_filter.return_value = expected_audio_bytes

        # Mock feature flag client that enables filtering
        mock_ff_client = Mock()
        mock_ff_client.is_enabled.return_value = True

        s3_objects = [Mock()]

        result = assemble_normalized_wav_from_s3_chunks(
            iter(s3_objects), mock_ff_client
        )

        assert result == expected_audio_bytes
        mock_download.assert_called_once()
        mock_normalize.assert_called_once()
        mock_filter.assert_called_once_with(normalized_audio)
        mock_ff_client.is_enabled.assert_called_once_with("audio_noise_filtering")

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_bytes_to_wav_bytes"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_skip_filtering_when_feature_flag_disabled(
        self, mock_download: Mock, mock_normalize: Mock
    ) -> None:
        """Test que le filtrage est ignoré quand le feature flag est désactivé."""

        mock_download.return_value = BytesIO(b"raw_audio")
        normalized_audio = BytesIO(b"normalized_audio")
        mock_normalize.return_value = normalized_audio

        # Mock feature flag client that disables filtering
        mock_ff_client = Mock()
        mock_ff_client.is_enabled.return_value = False

        s3_objects = [Mock()]

        result = assemble_normalized_wav_from_s3_chunks(
            iter(s3_objects), mock_ff_client
        )

        assert result == normalized_audio
        mock_download.assert_called_once()
        mock_normalize.assert_called_once()
        mock_ff_client.is_enabled.assert_called_once_with("audio_noise_filtering")
        # get_variant should not be called when disabled
        mock_ff_client.get_variant.assert_not_called()

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_bytes_to_wav_bytes"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_skip_filtering_when_no_feature_flag_client(
        self, mock_download: Mock, mock_normalize: Mock
    ) -> None:
        """Test que le filtrage est ignoré quand aucun client n'est fourni."""

        mock_download.return_value = BytesIO(b"raw_audio")
        normalized_audio = BytesIO(b"normalized_audio")
        mock_normalize.return_value = normalized_audio

        s3_objects = [Mock()]

        result = assemble_normalized_wav_from_s3_chunks(iter(s3_objects), None)

        assert result == normalized_audio
        mock_download.assert_called_once()
        mock_normalize.assert_called_once()
