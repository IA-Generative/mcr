from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcr_generation.app.exceptions.exceptions import MissingCustomPromptError
from mcr_generation.app.schemas.base import CustomMarkdownReport
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.schemas.custom_prompt import (
    CollectorSection,
    CustomSection,
    RewriterOutput,
)
from mcr_generation.app.services.report_generator import create_report_generator
from mcr_generation.app.services.report_generator.custom_report_generator import (
    CustomReportGenerator,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


@pytest.mark.asyncio
@patch(
    "mcr_generation.app.services.report_generator.custom_report_generator.METADATA_COLLECTORS"
)
async def test_generate_async_dispatches_collector_and_generic(
    mock_registry: MagicMock,
) -> None:
    mock_collector = MagicMock()
    mock_collector.collect = AsyncMock(return_value="- Alice\n- Bob")
    mock_registry.__getitem__.return_value = mock_collector

    plan = RewriterOutput(
        title="Réunion sprint",
        sections=[
            CollectorSection(heading="Participants", collector_id="participants"),
            CustomSection(heading="Risques", instruction="Liste les risques évoqués"),
        ],
    )

    gen = CustomReportGenerator(raw_prompt="prompt brut")
    gen.rewriter = MagicMock()
    gen.rewriter.rewrite = AsyncMock(return_value=plan)
    gen.pipeline = MagicMock()
    gen.pipeline.map_reduce_all_steps = AsyncMock(return_value="- R1\n- R2")

    chunks = [Chunk(text="contenu réunion", id=0)]
    report = await gen.generate_async(chunks)

    assert isinstance(report, CustomMarkdownReport)
    assert report.markdown_content == (
        "# Réunion sprint\n\n"
        "## Participants\n\n- Alice\n- Bob\n\n"
        "## Risques\n\n- R1\n- R2"
    )

    gen.rewriter.rewrite.assert_awaited_once_with("prompt brut")
    mock_collector.collect.assert_awaited_once_with(chunks)
    gen.pipeline.map_reduce_all_steps.assert_awaited_once_with(
        chunks, "Liste les risques évoqués"
    )


@pytest.mark.asyncio
async def test_generate_async_omits_h1_when_title_is_none() -> None:
    plan = RewriterOutput(
        title=None,
        sections=[CustomSection(heading="Risques", instruction="Liste les risques")],
    )
    gen = CustomReportGenerator(raw_prompt="prompt")
    gen.rewriter = MagicMock()
    gen.rewriter.rewrite = AsyncMock(return_value=plan)
    gen.pipeline = MagicMock()
    gen.pipeline.map_reduce_all_steps = AsyncMock(return_value="- R1")

    report = await gen.generate_async([Chunk(text="x", id=0)])

    assert report.markdown_content == "## Risques\n\n- R1"


def test_factory_threads_custom_prompt_into_generator() -> None:
    gen = create_report_generator(
        ReportTypes.CUSTOM_REPORT, custom_prompt="prompt utilisateur"
    )
    assert isinstance(gen, CustomReportGenerator)
    assert gen.raw_prompt == "prompt utilisateur"


def test_factory_raises_when_custom_prompt_missing() -> None:
    with pytest.raises(MissingCustomPromptError):
        create_report_generator(ReportTypes.CUSTOM_REPORT)
