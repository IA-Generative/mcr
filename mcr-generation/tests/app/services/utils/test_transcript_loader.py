import json
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

import pytest

from mcr_generation.app.exceptions.exceptions import TranscriptionFileNotFoundError
from mcr_generation.app.services.utils.input_chunker import Chunk
from mcr_generation.app.services.utils.transcript_loader import load_transcript_chunks

MODULE = "mcr_generation.app.services.utils.transcript_loader"

DOCX_KEY = "transcription/123/v0.docx"
FULL_TRANSCRIPT_KEY = "transcription/123/full_transcript.json"

FULL_TRANSCRIPT_JSON = json.dumps(
    {
        "meeting_id": 123,
        "version": 0,
        "segments": [
            {
                "speaker": "LOCUTEUR_00",
                "transcription_index": 0,
                "transcription": "bonjour",
                "start": 0.0,
                "end": 12.5,
            }
        ],
    }
).encode()


@pytest.fixture
def mock_get_file_from_s3(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    fn = MagicMock()
    monkeypatch.setattr(f"{MODULE}.get_file_from_s3", fn)
    return fn


@pytest.fixture
def mock_chunk_docx(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    fn = MagicMock(return_value=[Chunk(id=0, text="from docx")])
    monkeypatch.setattr(f"{MODULE}.chunk_docx_to_document_list", fn)
    return fn


def test_reads_the_full_transcript_json(
    mock_get_file_from_s3: MagicMock,
    mock_chunk_docx: MagicMock,
) -> None:
    mock_get_file_from_s3.return_value = BytesIO(FULL_TRANSCRIPT_JSON)

    chunks = load_transcript_chunks(DOCX_KEY)

    mock_get_file_from_s3.assert_called_once_with(FULL_TRANSCRIPT_KEY)
    mock_chunk_docx.assert_not_called()
    assert chunks == [Chunk(id=0, text="LOCUTEUR_00 : bonjour")]


def test_falls_back_to_the_docx_when_json_is_missing(
    mock_get_file_from_s3: MagicMock,
    mock_chunk_docx: MagicMock,
) -> None:
    docx_bytes = BytesIO(b"docx content")
    mock_get_file_from_s3.side_effect = [
        TranscriptionFileNotFoundError("no full_transcript.json"),
        docx_bytes,
    ]

    chunks = load_transcript_chunks(DOCX_KEY)

    assert [call.args[0] for call in mock_get_file_from_s3.call_args_list] == [
        FULL_TRANSCRIPT_KEY,
        DOCX_KEY,
    ]
    mock_chunk_docx.assert_called_once_with(docx_bytes)
    assert chunks == [Chunk(id=0, text="from docx")]


def test_propagates_corrupt_json(
    mock_get_file_from_s3: MagicMock,
    mock_chunk_docx: MagicMock,
) -> None:
    mock_get_file_from_s3.return_value = BytesIO(b"not json")

    with pytest.raises(ValueError):
        load_transcript_chunks(DOCX_KEY)

    mock_chunk_docx.assert_not_called()
