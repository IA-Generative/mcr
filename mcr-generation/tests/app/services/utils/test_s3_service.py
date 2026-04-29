"""Unit tests for services.utils.s3_service."""

from unittest.mock import MagicMock

import pytest

from mcr_generation.app.exceptions.exceptions import (
    MCRGenerationException,
    TranscriptionFileNotFoundError,
)
from mcr_generation.app.services.utils.s3_service import get_file_from_s3
from tests.mocks.s3_mocks import s3_client_error


class TestGetFileFromS3:
    def test_returns_bytesio_on_success(self, mock_s3_client: MagicMock) -> None:
        body = MagicMock()
        body.read.return_value = b"docx content"
        mock_s3_client.get_object.return_value = {"Body": body}

        result = get_file_from_s3("some/key.docx")

        assert result.read() == b"docx content"

    def test_raises_transcription_file_not_found_on_no_such_key(
        self, mock_s3_client: MagicMock
    ) -> None:
        mock_s3_client.get_object.side_effect = s3_client_error("NoSuchKey")

        with pytest.raises(
            TranscriptionFileNotFoundError,
            match="Transcription file not found in S3: missing.docx",
        ):
            get_file_from_s3("missing.docx")

    def test_raises_transcription_file_not_found_on_404(
        self, mock_s3_client: MagicMock
    ) -> None:
        mock_s3_client.get_object.side_effect = s3_client_error("404")

        with pytest.raises(TranscriptionFileNotFoundError):
            get_file_from_s3("missing.docx")

    def test_wraps_other_client_errors_as_generation_exception(
        self, mock_s3_client: MagicMock
    ) -> None:
        mock_s3_client.get_object.side_effect = s3_client_error("AccessDenied")

        with pytest.raises(
            MCRGenerationException,
            match="S3 download failed for some/key.docx",
        ):
            get_file_from_s3("some/key.docx")

    def test_wraps_unexpected_errors_as_generation_exception(
        self, mock_s3_client: MagicMock
    ) -> None:
        mock_s3_client.get_object.side_effect = RuntimeError("boom")

        with pytest.raises(
            MCRGenerationException,
            match="S3 download failed for some/key.docx",
        ):
            get_file_from_s3("some/key.docx")
