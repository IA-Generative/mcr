from unittest.mock import AsyncMock, patch

import pytest

from mcr_generation.app.services.generic_pipeline.pipeline import (
    GenericMapReducePipeline,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


@pytest.mark.asyncio
async def test_run_returns_empty_when_no_chunks() -> None:
    out = await GenericMapReducePipeline().run(chunks=[], instruction="anything")
    assert out == ""


@pytest.mark.asyncio
@patch.object(GenericMapReducePipeline, "_reduce", new_callable=AsyncMock)
@patch.object(GenericMapReducePipeline, "_map", new_callable=AsyncMock)
async def test_run_calls_map_then_reduce(
    mock_map: AsyncMock, mock_reduce: AsyncMock
) -> None:
    mock_map.return_value = ["fact 1", "fact 2"]
    mock_reduce.return_value = "## Résumé\n- fact 1\n- fact 2"
    chunks = [Chunk(text="x", id=0), Chunk(text="y", id=1)]

    out = await GenericMapReducePipeline().run(chunks, "résume")

    mock_map.assert_awaited_once()
    mock_reduce.assert_awaited_once_with(["fact 1", "fact 2"], "résume")
    assert "Résumé" in out


@pytest.mark.asyncio
@patch.object(GenericMapReducePipeline, "_reduce", new_callable=AsyncMock)
@patch.object(GenericMapReducePipeline, "_map", new_callable=AsyncMock)
async def test_run_skips_reduce_when_no_facts(
    mock_map: AsyncMock, mock_reduce: AsyncMock
) -> None:
    mock_map.return_value = []
    out = await GenericMapReducePipeline().run([Chunk(text="x", id=0)], "résume")
    assert out == ""
    mock_reduce.assert_not_awaited()
