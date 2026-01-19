from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.schemas.S3_types import S3Object
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    download_and_concatenate_s3_audio_chunks_into_file,
)


class TestDownloadAndConcatenateS3AudioChunks:
    """Tests pour la fonction download_and_concatenate_s3_audio_chunks_into_file."""

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.get_file_from_s3"
    )
    def test_should_raise_invalid_audio_file_error_when_s3_download_fails(
        self, mock_get_file_from_s3
    ):
        """Test que la fonction gère les échecs de téléchargement S3."""
        mock_get_file_from_s3.side_effect = ConnectionError("S3 connection timeout")

        s3_objects = [
            S3Object(
                bucket_name="test-bucket",
                object_name="123/audio_chunk_1.weba",
                last_modified="2023-01-01T00:00:00Z",
            )
        ]
        mock_file = Mock()

        with pytest.raises(InvalidAudioFileError) as exc_info:
            download_and_concatenate_s3_audio_chunks_into_file(
                iter(s3_objects), mock_file
            )

        assert "Failed to download audio chunk 123/audio_chunk_1.weba" in str(
            exc_info.value
        )
        assert "S3 connection timeout" in str(exc_info.value)

        mock_file.write.assert_not_called()

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.get_file_from_s3"
    )
    def test_should_process_successfully_when_valid_chunks(self, mock_get_file_from_s3):
        """Test le traitement réussi de chunks audio valides."""
        mock_get_file_from_s3.side_effect = [
            BytesIO(b"audio_data_1"),
            BytesIO(b"audio_data_2"),
            BytesIO(b"audio_data_3"),
        ]

        s3_objects = [
            S3Object(
                bucket_name="test-bucket",
                object_name="123/audio_chunk_1.weba",
                last_modified="2023-01-01T00:00:00Z",
            ),
            S3Object(
                bucket_name="test-bucket",
                object_name="123/audio_chunk_2.weba",
                last_modified="2023-01-01T00:01:00Z",
            ),
            S3Object(
                bucket_name="test-bucket",
                object_name="123/audio_chunk_3.weba",
                last_modified="2023-01-01T00:02:00Z",
            ),
        ]
        mock_file = Mock()

        download_and_concatenate_s3_audio_chunks_into_file(iter(s3_objects), mock_file)

        assert mock_file.write.call_count == 3
        mock_file.write.assert_any_call(b"audio_data_1")
        mock_file.write.assert_any_call(b"audio_data_2")
        mock_file.write.assert_any_call(b"audio_data_3")
        mock_file.flush.assert_called_once()
        mock_file.seek.assert_called_once_with(0)

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.get_file_from_s3"
    )
    def test_should_handle_empty_chunks_gracefully(self, mock_get_file_from_s3):
        """Test la gestion des chunks vides."""
        mock_get_file_from_s3.side_effect = [
            BytesIO(b""),
            BytesIO(b"valid_data"),
            BytesIO(b""),
        ]  # Chunks vides mélangés
        s3_objects = [
            S3Object(
                bucket_name="test",
                object_name="123/chunk1.weba",
                last_modified="2023-01-01T00:00:00Z",
            ),
            S3Object(
                bucket_name="test",
                object_name="123/chunk2.weba",
                last_modified="2023-01-01T00:01:00Z",
            ),
            S3Object(
                bucket_name="test",
                object_name="123/chunk3.weba",
                last_modified="2023-01-01T00:02:00Z",
            ),
        ]
        mock_file = Mock()

        download_and_concatenate_s3_audio_chunks_into_file(iter(s3_objects), mock_file)
        assert mock_file.write.call_count == 3
        mock_file.write.assert_any_call(b"")
        mock_file.write.assert_any_call(b"valid_data")
        mock_file.write.assert_any_call(b"")
        mock_file.flush.assert_called_once()
        mock_file.seek.assert_called_once_with(0)

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.get_file_from_s3"
    )
    def test_should_handle_single_chunk_successfully(self, mock_get_file_from_s3):
        """Test le traitement réussi d'un seul chunk."""
        mock_get_file_from_s3.return_value = BytesIO(b"single_audio_data")

        s3_objects = [
            S3Object(
                bucket_name="test-bucket",
                object_name="123/single_chunk.weba",
                last_modified="2023-01-01T00:00:00Z",
            )
        ]
        mock_file = Mock()

        download_and_concatenate_s3_audio_chunks_into_file(iter(s3_objects), mock_file)

        mock_file.write.assert_called_once_with(b"single_audio_data")
        mock_file.flush.assert_called_once()
        mock_file.seek.assert_called_once_with(0)

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.get_file_from_s3"
    )
    def test_should_handle_large_number_of_chunks(self, mock_get_file_from_s3):
        """Test le traitement d'un grand nombre de chunks."""
        num_chunks = 50
        mock_get_file_from_s3.side_effect = [
            BytesIO(f"chunk_data_{i}".encode()) for i in range(num_chunks)
        ]

        s3_objects = [
            S3Object(
                bucket_name="test-bucket",
                object_name=f"123/chunk_{i}.weba",
                last_modified="2023-01-01T00:00:00Z",
            )
            for i in range(num_chunks)
        ]
        mock_file = Mock()

        download_and_concatenate_s3_audio_chunks_into_file(iter(s3_objects), mock_file)

        assert mock_file.write.call_count == num_chunks
        mock_file.flush.assert_called_once()
        mock_file.seek.assert_called_once_with(0)

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.get_file_from_s3"
    )
    def test_should_handle_different_s3_error_types(self, mock_get_file_from_s3):
        """Test la gestion de différents types d'erreurs S3."""
        error_test_cases = [
            (ConnectionError("Connection timeout"), "Connection timeout"),
            (TimeoutError("Request timeout"), "Request timeout"),
            (PermissionError("Access denied"), "Access denied"),
            (Exception("Generic S3 error"), "Generic S3 error"),
        ]

        for error, expected_message in error_test_cases:
            mock_get_file_from_s3.side_effect = error

            s3_objects = [
                S3Object(
                    bucket_name="test-bucket",
                    object_name="123/test_chunk.weba",
                    last_modified="2023-01-01T00:00:00Z",
                )
            ]
            mock_file = Mock()

            with pytest.raises(InvalidAudioFileError) as exc_info:
                download_and_concatenate_s3_audio_chunks_into_file(
                    iter(s3_objects), mock_file
                )

            assert expected_message in str(exc_info.value)
            assert "Failed to download audio chunk 123/test_chunk.weba" in str(
                exc_info.value
            )

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.get_file_from_s3"
    )
    def test_should_work_with_real_file_object(self, mock_get_file_from_s3):
        """Test avec un vrai objet fichier BytesIO."""
        mock_get_file_from_s3.side_effect = [BytesIO(b"chunk1"), BytesIO(b"chunk2")]

        s3_objects = [
            S3Object(
                bucket_name="test",
                object_name="123/chunk1.weba",
                last_modified="2023-01-01T00:00:00Z",
            ),
            S3Object(
                bucket_name="test",
                object_name="123/chunk2.weba",
                last_modified="2023-01-01T00:01:00Z",
            ),
        ]

        with BytesIO() as real_file:
            download_and_concatenate_s3_audio_chunks_into_file(
                iter(s3_objects), real_file
            )

            real_file.seek(0)
            content = real_file.read()
            assert content == b"chunk1chunk2"
