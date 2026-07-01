"""Pure text splitting and segment reconstruction for the LLM correctors."""

import re

from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from mcr_meeting.app.configs.base import ChunkingConfig
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment

_chunk_config = ChunkingConfig()


def format_segments_for_llm(segments: list[DiarizedTranscriptionSegment]) -> str:
    if not segments:
        return ""
    return (
        "".join(
            segment.text.strip() + f" <separator{i}>"
            for i, segment in enumerate(segments[:-1], start=1)
        )
        + segments[-1].text.strip()
    )


def chunk_text(text: str, *, chunk_overlap: int = 0) -> list[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=_chunk_config.CHUNK_SIZE,
        chunk_overlap=chunk_overlap,
    )
    chunked_text = text_splitter.split_text(text)
    logger.debug("Nb of chunked documents: {}", len(chunked_text))
    return chunked_text


def reassemble_corrected_segments(
    corrected_chunks: list[str],
    segments: list[DiarizedTranscriptionSegment],
) -> list[DiarizedTranscriptionSegment]:
    segment_texts = _split_segments(corrected_chunks, len(segments))
    return _replace_corrected_segments(segments, segment_texts)


def _split_segments(
    corrected_chunks: list[str], expected_segments_count: int
) -> dict[int, str | None]:
    text = " ".join(corrected_chunks)

    parts = re.split(r"<separator(\d+)>", text)

    segment_texts: dict[int, str | None] = {
        segment_id: None for segment_id in range(expected_segments_count)
    }

    segment_texts[0] = parts[0] if parts else text

    found_separator_ids = _fill_segment_texts_from_parts(
        parts=parts,
        segment_texts=segment_texts,
    )
    _invalidate_missing_separators(
        found_separator_ids=found_separator_ids,
        segment_texts=segment_texts,
        expected_segments_count=expected_segments_count,
    )

    return segment_texts


def _fill_segment_texts_from_parts(
    parts: list[str],
    segment_texts: dict[int, str | None],
) -> set[int]:
    found_separator_ids: set[int] = set()
    for index in range(1, len(parts), 2):
        segment_id = int(parts[index])
        if segment_id in segment_texts:
            found_separator_ids.add(segment_id)
            segment_texts[segment_id] = parts[index + 1]

    return found_separator_ids


def _invalidate_missing_separators(
    found_separator_ids: set[int],
    segment_texts: dict[int, str | None],
    expected_segments_count: int,
) -> None:
    for separator_id in range(1, expected_segments_count):
        if separator_id not in found_separator_ids:
            segment_texts[separator_id] = None
            if separator_id > 1:
                segment_texts[separator_id - 1] = None


def _replace_corrected_segments(
    segments: list[DiarizedTranscriptionSegment],
    segment_texts: dict[int, str | None],
) -> list[DiarizedTranscriptionSegment]:
    replaced_segments: list[DiarizedTranscriptionSegment] = []

    for segment_id, segment in enumerate(segments):
        corrected_text = segment_texts.get(segment_id)
        if corrected_text is None:
            logger.debug(
                "No corrected text found for segment {}, keeping original text",
                segment_id,
            )
        else:
            segment = segment.model_copy(update={"text": corrected_text})
        replaced_segments.append(segment)

    return replaced_segments
