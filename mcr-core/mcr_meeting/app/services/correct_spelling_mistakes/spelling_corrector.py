import re

from loguru import logger
from pydantic import BaseModel

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.correct_spelling_mistakes.prompt import PROMPT_TEMPLATE
from mcr_meeting.app.services.llm_post_processing import Chunk, LLMPostProcessing


class CorrectedText(BaseModel):
    corrected_text: str


class SpellingCorrector(LLMPostProcessing):
    def __init__(self) -> None:
        super().__init__()

    def correct(
        self, segments: list[DiarizedTranscriptionSegment]
    ) -> list[DiarizedTranscriptionSegment]:
        """
        Corrects spelling mistakes in the given segments using an LLM.

        Args:
            segments (list[DiarizedTranscriptionSegment]): List of diarized transcription segments.

        Returns:
            list[DiarizedTranscriptionSegment]: List of segments with corrected text.
        """
        if not segments:
            logger.warning("No segments found to correct")
            return []

        text = self._format_segments_for_llm(segments)
        chunks = self._chunk_text(text, chunk_overlap=0)

        for chunk in chunks:
            chunk.text = self._correct_chunk(chunk)

        segment_texts = self._split_segments(
            chunks=chunks,
            expected_segments_count=len(segments),
        )

        return self._replace_corrected_segments(segments, segment_texts)

    def _format_segments_for_llm(
        self, segments: list[DiarizedTranscriptionSegment]
    ) -> str:
        """
        Helper to convert segments into a dialogue string.

        Args:
            segments (list[DiarizedTranscriptionSegment]): List of speaker transcriptions.

        Returns:
            str: Dialogue string.
        """
        return (
            "".join(
                segment.text.strip() + f" <separator{i}>"
                for i, segment in enumerate(segments[:-1], start=1)
            )
            + segments[-1].text.strip()
        )

    def _correct_chunk(self, chunk: Chunk) -> str:
        result = self.client.chat.completions.create(
            model=self.settings.LLM_MODEL_NAME,
            response_model=CorrectedText,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(text=chunk.text),
                }
            ],
        )
        return result.corrected_text

    def _split_segments(
        self, chunks: list[Chunk], expected_segments_count: int
    ) -> dict[int, str | None]:
        text = " ".join(chunk.text for chunk in chunks)

        # Split on <separatorID> and capture the ID "A<separator1>B<separator2>C" becomes ["A", "1", "B", "2", "C"]
        parts = re.split(r"<separator(\d+)>", text)

        # Create a mapping of segment ID to corrected text, initializing with None
        segment_texts: dict[int, str | None] = {
            segment_id: None for segment_id in range(expected_segments_count)
        }

        # The first part before any separator is the text of the first segment
        segment_texts[0] = parts[0] if parts else text

        found_separator_ids = self._fill_segment_texts_from_parts(
            parts=parts,
            segment_texts=segment_texts,
        )
        self._invalidate_missing_separators(
            found_separator_ids=found_separator_ids,
            segment_texts=segment_texts,
            expected_segments_count=expected_segments_count,
        )

        return segment_texts

    def _fill_segment_texts_from_parts(
        self,
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
        self,
        found_separator_ids: set[int],
        segment_texts: dict[int, str | None],
        expected_segments_count: int,
    ) -> None:
        for separator_id in range(1, expected_segments_count):
            if separator_id not in found_separator_ids:
                segment_texts[separator_id] = None
                # Keep the first segment text when separator1 is missing.
                if separator_id > 1:
                    segment_texts[separator_id - 1] = None

    def _replace_corrected_segments(
        self,
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
