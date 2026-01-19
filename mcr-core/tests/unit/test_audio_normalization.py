from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.schemas.S3_types import S3Object
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    assemble_normalized_wav_from_s3_chunks,
)


class TestAssembleNormalizedWavFromS3Chunks:
    """Tests pour la fonction assemble_normalized_wav_from_s3_chunks."""

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_file"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_file_to_wav_bytes"
    )
    def test_should_raise_invalid_audio_file_error_when_download_fails(
        self, mock_normalize, mock_download
    ):
        """Test que la fonction gère les échecs de téléchargement."""
        mock_download.side_effect = InvalidAudioFileError(
            "No audio chunks found to process"
        )

        empty_chunk_list = [Mock()]

        with pytest.raises(
            InvalidAudioFileError, match="No audio chunks found to process"
        ):
            assemble_normalized_wav_from_s3_chunks(iter(empty_chunk_list), "weba")

        mock_normalize.assert_not_called()

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_file"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_file_to_wav_bytes"
    )
    def test_should_return_normalized_audio_bytes_when_successful(
        self, mock_normalize, mock_download
    ):
        """Test le succès de l'assemblage et normalisation."""
        mock_download.return_value = None
        expected_audio_bytes = b"normalized_wav_data_12345"
        mock_normalize.return_value = expected_audio_bytes

        s3_objects = [Mock()]

        result = assemble_normalized_wav_from_s3_chunks(iter(s3_objects), "weba")

        assert result == expected_audio_bytes
        mock_download.assert_called_once()
        mock_normalize.assert_called_once()

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_file"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_file_to_wav_bytes"
    )
    def test_should_handle_different_audio_extensions(
        self, mock_normalize, mock_download
    ):
        """Test la gestion de différentes extensions audio."""
        mock_download.return_value = None
        mock_normalize.return_value = b"normalized_audio"

        test_extensions = ["weba", "mp3", "wav", "m4a", "ogg", "flac"]

        for extension in test_extensions:
            s3_objects = [Mock()]

            result = assemble_normalized_wav_from_s3_chunks(iter(s3_objects), extension)

            assert result == b"normalized_audio"

            mock_download.assert_called()

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_file"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_file_to_wav_bytes"
    )
    def test_should_handle_empty_extension(self, mock_normalize, mock_download):
        """Test la gestion d'une extension vide."""
        mock_download.return_value = None
        mock_normalize.return_value = b"normalized_audio"

        s3_objects = [Mock()]

        result = assemble_normalized_wav_from_s3_chunks(iter(s3_objects), "")

        assert result == b"normalized_audio"

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_file"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_file_to_wav_bytes"
    )
    def test_should_verify_temporary_file_creation(self, mock_normalize, mock_download):
        """Test que les fichiers temporaires sont créés correctement."""
        mock_download.return_value = None
        mock_normalize.return_value = b"test_audio"

        s3_objects = [Mock()]

        result = assemble_normalized_wav_from_s3_chunks(iter(s3_objects), "weba")

        assert result == b"test_audio"
        mock_normalize.assert_called_once()
        call_args = mock_normalize.call_args[0]
        assert len(call_args) == 1
        assert isinstance(call_args[0], str)

    def test_should_handle_real_s3_objects(self):
        """Test avec de vrais objets S3Object."""
        s3_objects = [
            S3Object(
                bucket_name="test-bucket",
                object_name="123/chunk1.weba",
                last_modified="2023-01-01T00:00:00Z",
            ),
            S3Object(
                bucket_name="test-bucket",
                object_name="123/chunk2.weba",
                last_modified="2023-01-01T00:01:00Z",
            ),
        ]

        with (
            patch(
                "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_file"
            ) as mock_download,
            patch(
                "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_file_to_wav_bytes"
            ) as mock_normalize,
        ):
            mock_download.return_value = None
            mock_normalize.return_value = b"real_audio_data"

            result = assemble_normalized_wav_from_s3_chunks(iter(s3_objects), "weba")

            assert result == b"real_audio_data"
            mock_download.assert_called_once()
            mock_normalize.assert_called_once()

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_file"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_file_to_wav_bytes"
    )
    def test_should_handle_large_audio_data(self, mock_normalize, mock_download):
        """Test la gestion de gros fichiers audio."""
        mock_download.return_value = None
        large_audio_data = b"x" * (1024 * 1024)
        mock_normalize.return_value = large_audio_data

        s3_objects = [Mock()]

        result = assemble_normalized_wav_from_s3_chunks(iter(s3_objects), "weba")

        assert result == large_audio_data
        assert len(result) == 1024 * 1024
