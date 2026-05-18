from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from mcr_generation.app.exceptions.exceptions import EmptyChunksError
from mcr_generation.app.services.generic_pipeline.generic_map_reduce_pipeline import (
    GenericMapReducePipeline,
    _ReduceResponse,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


@pytest.mark.asyncio
async def test_run_raises_when_no_chunks() -> None:
    with pytest.raises(EmptyChunksError):
        await GenericMapReducePipeline().map_reduce_all_steps(
            chunks=[], instruction="anything"
        )


@pytest.mark.asyncio
@patch.object(GenericMapReducePipeline, "_reduce", new_callable=AsyncMock)
@patch.object(GenericMapReducePipeline, "_map", new_callable=AsyncMock)
async def test_run_calls_map_then_reduce(
    mock_map: AsyncMock, mock_reduce: AsyncMock
) -> None:
    mock_map.return_value = ["fact 1", "fact 2"]
    mock_reduce.return_value = "## Résumé\n- fact 1\n- fact 2"
    chunks = [Chunk(text="x", id=0), Chunk(text="y", id=1)]

    out = await GenericMapReducePipeline().map_reduce_all_steps(chunks, "résume")

    mock_map.assert_awaited_once()
    mock_reduce.assert_awaited_once_with(["fact 1", "fact 2"], "résume")
    assert "Résumé" in out


@pytest.mark.asyncio
@patch(
    "mcr_generation.app.services.generic_pipeline.generic_map_reduce_pipeline.record_empty_map_phase_event"
)
@patch.object(GenericMapReducePipeline, "_reduce", new_callable=AsyncMock)
@patch.object(GenericMapReducePipeline, "_map", new_callable=AsyncMock)
async def test_run_skips_reduce_when_no_facts(
    mock_map: AsyncMock,
    mock_reduce: AsyncMock,
    mock_record_event: AsyncMock,
) -> None:
    mock_map.return_value = []
    out = await GenericMapReducePipeline().map_reduce_all_steps(
        [Chunk(text="x", id=0)], "résume"
    )
    assert out == ""
    mock_reduce.assert_not_awaited()
    mock_record_event.assert_called_once_with(
        section="generic_pipeline",
        chunk_count=1,
    )


class TestReduceResponseHeadingValidator:
    def test_rejects_h1_at_start(self) -> None:
        with pytest.raises(ValidationError, match="top-level headings"):
            _ReduceResponse(markdown="# Titre\n\nCorps du texte.")

    def test_rejects_h2_at_start(self) -> None:
        with pytest.raises(ValidationError, match="top-level headings"):
            _ReduceResponse(markdown="## Sous-titre\n\nCorps.")

    def test_rejects_h1_in_middle(self) -> None:
        with pytest.raises(ValidationError, match="top-level headings"):
            _ReduceResponse(markdown="Intro.\n\n# Titre tardif\n\nSuite.")

    def test_rejects_h2_in_middle(self) -> None:
        with pytest.raises(ValidationError, match="top-level headings"):
            _ReduceResponse(markdown="Intro.\n\n## Tardif.\n\nSuite.")

    def test_accepts_h3_h4_h5_h6(self) -> None:
        md = "### h3\n#### h4\n##### h5\n###### h6\nParagraphe."
        assert _ReduceResponse(markdown=md).markdown == md

    def test_accepts_hash_inside_word(self) -> None:
        md = "Couleur #ff0000 et issue #123 dans le PR."
        assert _ReduceResponse(markdown=md).markdown == md

    def test_accepts_hash_without_space(self) -> None:
        md = "Tags : #urgent #refacto"
        assert _ReduceResponse(markdown=md).markdown == md

    def test_accepts_short_no_content_message(self) -> None:
        md = "Aucun élément pertinent dans le transcript."
        assert _ReduceResponse(markdown=md).markdown == md
