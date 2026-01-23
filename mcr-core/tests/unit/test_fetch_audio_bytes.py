from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.services.meeting_to_transcription_service import fetch_audio_bytes


@pytest.fixture(autouse=True)
def mock_ff_singleton():
    """Mock FeatureFlagSingleton to prevent Unleash initialization during tests."""
    with patch(
        "mcr_meeting.app.services.feature_flag_service.FeatureFlagSingleton"
    ) as mock:
        yield mock


class TestFetchAudioBytes:
    """Tests pour la fonction fetch_audio_bytes."""

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_raise_invalid_audio_file_error_when_no_audio_files_found(
        self, mock_get_ff_client: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que fetch_audio_bytes lève ValueError quand aucun fichier audio n'est trouvé."""
        mock_get_objects_list.return_value = iter([])
        mock_ff_client = Mock()
        mock_get_ff_client.return_value = mock_ff_client

        with pytest.raises(ValueError, match="No audio files found for meeting 123"):
            fetch_audio_bytes(meeting_id=123)

        mock_get_objects_list.assert_called_once_with(prefix="123/")

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.assemble_normalized_wav_from_s3_chunks"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_raise_invalid_audio_file_error_when_audio_processing_fails(
        self, mock_get_ff_client: Mock, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que fetch_audio_bytes lève Exception quand le traitement audio échoue."""
        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.side_effect = InvalidAudioFileError("Processing failed")
        mock_ff_client = Mock()
        mock_get_ff_client.return_value = mock_ff_client

        with pytest.raises(Exception, match="Audio processing failed for meeting 123"):
            fetch_audio_bytes(meeting_id=123)

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.assemble_normalized_wav_from_s3_chunks"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_raise_invalid_audio_file_error_when_extension_extraction_fails(
        self, mock_get_ff_client: Mock, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que fetch_audio_bytes lève ValueError quand l'extraction d'extension échoue."""
        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.side_effect = ValueError(
            "No audio files found for the specified meeting"
        )
        mock_ff_client = Mock()
        mock_get_ff_client.return_value = mock_ff_client

        with pytest.raises(ValueError, match="No audio files found for meeting 123"):
            fetch_audio_bytes(meeting_id=123)

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.assemble_normalized_wav_from_s3_chunks"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_raise_invalid_audio_file_error_when_unexpected_error_occurs(
        self, mock_get_ff_client: Mock, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que fetch_audio_bytes lève Exception pour toute erreur inattendue."""
        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.side_effect = RuntimeError("Unexpected error")
        mock_ff_client = Mock()
        mock_get_ff_client.return_value = mock_ff_client

        with pytest.raises(
            Exception, match="Failed to fetch audio bytes for meeting 123"
        ):
            fetch_audio_bytes(meeting_id=123)

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.assemble_normalized_wav_from_s3_chunks"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_return_audio_bytes_when_successful(
        self, mock_get_ff_client: Mock, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que fetch_audio_bytes retourne les bytes audio en cas de succès."""

        expected_audio_bytes = BytesIO(b"audio_data_normalized_12345")

        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.return_value = expected_audio_bytes
        mock_ff_client = Mock()
        mock_get_ff_client.return_value = mock_ff_client

        result = fetch_audio_bytes(meeting_id=123)

        assert result == expected_audio_bytes
        mock_get_objects_list.assert_called_once_with(prefix="123/")
        mock_assemble.assert_called_once()

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.assemble_normalized_wav_from_s3_chunks"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_handle_different_meeting_ids(
        self, mock_get_ff_client: Mock, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que fetch_audio_bytes gère correctement différents IDs de meeting."""

        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.return_value = BytesIO(b"audio_data")

        test_meeting_ids = [1, 123, 9999, 100000]

        for meeting_id in test_meeting_ids:
            result = fetch_audio_bytes(meeting_id=meeting_id)

            assert result.getvalue() == b"audio_data"
            expected_prefix = f"{meeting_id}/"
            mock_get_objects_list.assert_called_with(prefix=expected_prefix)

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.assemble_normalized_wav_from_s3_chunks"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_handle_different_audio_extensions(
        self, mock_get_ff_client: Mock, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que fetch_audio_bytes gère correctement différentes extensions audio."""

        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.return_value = BytesIO(b"audio_data")

        # Since the service no longer deals with extensions directly,
        # we just test that it processes the audio correctly
        result = fetch_audio_bytes(meeting_id=123)
        assert result.getvalue() == b"audio_data"
        mock_assemble.assert_called_once()

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.assemble_normalized_wav_from_s3_chunks"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_handle_different_error_types_from_assemble(
        self, mock_get_ff_client: Mock, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que fetch_audio_bytes gère correctement différents types d'erreurs depuis assemble_normalized_wav_from_s3_chunks."""
        mock_get_objects_list.return_value = iter([Mock()])

        error_test_cases = [
            InvalidAudioFileError("No audio chunks found"),
            InvalidAudioFileError("FFmpeg failed"),
            InvalidAudioFileError("Normalization error"),
        ]

        for error in error_test_cases:
            mock_assemble.side_effect = error

            with pytest.raises(Exception):
                fetch_audio_bytes(meeting_id=123)

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.assemble_normalized_wav_from_s3_chunks"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_handle_empty_audio_bytes(
        self, mock_get_ff_client: Mock, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que fetch_audio_bytes gère correctement les bytes audio vides."""

        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.return_value = BytesIO(b"")

        result = fetch_audio_bytes(meeting_id=123)

        assert result.getvalue() == b""

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.assemble_normalized_wav_from_s3_chunks"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_handle_large_audio_files(
        self, mock_get_ff_client: Mock, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que fetch_audio_bytes gère correctement les gros fichiers audio."""

        mock_get_objects_list.return_value = iter([Mock()])

        large_audio_data = b"x" * (5 * 1024 * 1024)
        mock_assemble.return_value = BytesIO(large_audio_data)

        result = fetch_audio_bytes(meeting_id=123)

        assert result.getvalue() == large_audio_data
        assert len(result.getvalue()) == 5 * 1024 * 1024

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_feature_flag_client"
    )
    def test_should_call_get_objects_list_with_correct_prefix_format(
        self, mock_get_ff_client: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Test que get_objects_list_from_prefix est appelé avec le bon format de préfixe."""
        mock_get_objects_list.return_value = iter([])

        meeting_id = 42
        with pytest.raises(ValueError):
            fetch_audio_bytes(meeting_id=meeting_id)

        mock_get_objects_list.assert_called_once_with(prefix="42/")

        for test_id in [1, 999, 123456]:
            mock_get_objects_list.reset_mock()
            with pytest.raises(ValueError):
                fetch_audio_bytes(meeting_id=test_id)
            mock_get_objects_list.assert_called_once_with(prefix=f"{test_id}/")
