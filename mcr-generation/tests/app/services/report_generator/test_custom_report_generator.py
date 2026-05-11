"""Unit tests for CustomReportGenerator (T1b)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcr_generation.app.exceptions.exceptions import MissingCustomPromptError
from mcr_generation.app.schemas.base import CustomMarkdownReport
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.report_generator import create_report_generator
from mcr_generation.app.services.report_generator.custom_report_generator import (
    CustomReportGenerator,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


@pytest.mark.asyncio
async def test_generate_async_runs_pipeline_with_provided_instruction() -> None:
    gen = CustomReportGenerator(instruction="résume les risques")
    gen.pipeline = MagicMock()
    gen.pipeline.map_reduce_all_steps = AsyncMock(
        return_value="## Risques\n- R1\n## Actions\n- A1"
    )

    chunks = [Chunk(text="contenu réunion", id=0)]
    report = await gen.generate_async(chunks)

    assert isinstance(report, CustomMarkdownReport)
    assert report.markdown_content.startswith("## Risques")

    gen.pipeline.map_reduce_all_steps.assert_awaited_once_with(
        chunks, "résume les risques"
    )


def test_factory_threads_custom_prompt_into_generator() -> None:
    gen = create_report_generator(
        ReportTypes.CUSTOM_REPORT, custom_prompt="prompt utilisateur"
    )
    assert isinstance(gen, CustomReportGenerator)
    assert gen.instruction == "prompt utilisateur"


def test_factory_raises_when_custom_prompt_missing() -> None:
    with pytest.raises(MissingCustomPromptError):
        create_report_generator(ReportTypes.CUSTOM_REPORT)
