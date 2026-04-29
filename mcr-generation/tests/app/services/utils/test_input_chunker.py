"""Unit tests for services.utils.input_chunker."""

from io import BytesIO
from unittest.mock import MagicMock

import pytest

from mcr_generation.app.exceptions.exceptions import InvalidTranscriptionFileError
from mcr_generation.app.services.utils.input_chunker import chunk_docx_to_document_list


class TestChunkDocxToDocumentList:
    def test_wraps_loader_errors_as_invalid_transcription_file_error(
        self, mock_docx_loader: MagicMock
    ) -> None:
        mock_docx_loader.return_value.load.side_effect = RuntimeError("corrupted docx")

        with pytest.raises(
            InvalidTranscriptionFileError,
            match="Failed to parse DOCX transcription",
        ):
            chunk_docx_to_document_list(BytesIO(b"not a real docx"))
