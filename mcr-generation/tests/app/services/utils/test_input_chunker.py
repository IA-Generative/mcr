"""Unit tests for services.utils.input_chunker."""

from io import BytesIO
from unittest.mock import MagicMock

import pytest

from mcr_generation.app.exceptions.exceptions import InvalidTranscriptionFileError
from mcr_generation.app.schemas.transcript import FullTranscript, FullTranscriptSegment
from mcr_generation.app.services.utils.input_chunker import (
    chunk_docx_to_document_list,
    chunk_transcript_to_document_list,
)


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


def _full_transcript(segments: list[tuple[str, str]]) -> FullTranscript:
    return FullTranscript(
        meeting_id=123,
        segments=[
            FullTranscriptSegment(
                speaker=speaker,
                transcription_index=index,
                transcription=text,
                start=float(index),
                end=float(index + 1),
            )
            for index, (speaker, text) in enumerate(segments)
        ],
    )


class TestChunkTranscriptToDocumentList:
    def test_renders_segments_like_the_docx_layout(self) -> None:
        transcript = _full_transcript(
            [("LOCUTEUR_00", "bonjour"), ("LOCUTEUR_01", "salut")]
        )

        chunks = chunk_transcript_to_document_list(transcript)

        assert len(chunks) == 1
        assert chunks[0].id == 0
        assert chunks[0].text == "LOCUTEUR_00 : bonjour\nLOCUTEUR_01 : salut"

    def test_returns_no_chunks_for_empty_transcript(self) -> None:
        chunks = chunk_transcript_to_document_list(_full_transcript([]))

        assert chunks == []
