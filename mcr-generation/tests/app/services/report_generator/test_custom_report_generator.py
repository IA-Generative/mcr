"""Unit tests for CustomReportGenerator (T1b)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.schemas.custom_markdown_report import CustomMarkdownReport
from mcr_generation.app.services.report_generator import get_generator
from mcr_generation.app.services.report_generator.custom_report_generator import (
    DEFAULT_INSTRUCTION,
    CustomReportGenerator,
    _resolve_instruction,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


@pytest.mark.asyncio
async def test_generate_async_runs_pipeline_with_resolved_instruction() -> None:
    gen = CustomReportGenerator()
    gen.pipeline = MagicMock()
    gen.pipeline.map_reduce_all_steps = AsyncMock(
        return_value="## Risques\n- R1\n## Actions\n- A1"
    )

    chunks = [Chunk(text="contenu réunion", id=0)]
    report = await gen.generate_async(chunks)

    assert isinstance(report, CustomMarkdownReport)
    assert report.markdown.startswith("## Risques")

    gen.pipeline.map_reduce_all_steps.assert_awaited_once()
    args, _ = gen.pipeline.map_reduce_all_steps.call_args
    assert args[0] == chunks
    assert args[1] == DEFAULT_INSTRUCTION


def test_resolve_instruction_returns_default_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CUSTOM_USER_PROMPT_FOR_TESTING", raising=False)
    assert _resolve_instruction() == DEFAULT_INSTRUCTION


def test_resolve_instruction_env_override_takes_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUSTOM_USER_PROMPT_FOR_TESTING", "instruction de test")
    assert _resolve_instruction() == "instruction de test"


def test_factory_returns_custom_generator() -> None:
    assert isinstance(get_generator(ReportTypes.CUSTOM), CustomReportGenerator)
