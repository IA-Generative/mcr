"""The AI gateway cuts an idle upstream connection after one hour.
Every MCR client must wait that long before it gives up, otherwise it closes
the socket first and the gateway logs a 499."""

from collections.abc import Callable

import pytest
from openai import AsyncOpenAI, OpenAI

from mcr_generation.app.configs.settings import LLMConfig

GATEWAY_TIMEOUT_SECONDS = 3600.0


def test_configured_timeout_matches_the_gateway_ceiling() -> None:
    assert LLMConfig().LLM_API_TIMEOUT == GATEWAY_TIMEOUT_SECONDS


def _build_rewriter() -> object:
    from mcr_generation.app.services.rewriter.rewriter import Rewriter

    return Rewriter()


def _build_minutes_synthesizer() -> object:
    from mcr_generation.app.services.sections.minutes_synthesis.minutes_synthesizer import (
        MinutesSynthesizer,
    )

    return MinutesSynthesizer()


def _build_discussions_synthesizer() -> object:
    from mcr_generation.app.services.sections.discussions_synthesis.detailed_discussions_synthesizer import (
        DetailedDiscussionsSynthesizer,
    )

    return DetailedDiscussionsSynthesizer()


def _build_notes_extractor() -> object:
    from mcr_generation.app.services.notes.notes_extractor import NotesExtractor

    return NotesExtractor()


def _build_generic_pipeline() -> object:
    from mcr_generation.app.services.generic_pipeline.generic_map_reduce_pipeline import (
        GenericMapReducePipeline,
    )

    return GenericMapReducePipeline()


def _build_map_reduce_section() -> object:
    from mcr_generation.app.services.sections.base.map_reduce import BaseMapReduce

    return BaseMapReduce()


def _build_init_then_refine_section() -> object:
    from mcr_generation.app.services.sections.base.init_then_refine import (
        BaseInitThenRefine,
    )

    return BaseInitThenRefine()


def _build_g_eval_scorer() -> object:
    from mcr_generation.evaluation.scorers.g_eval import GEvalScorer

    return GEvalScorer()


@pytest.mark.parametrize(
    "build",
    [
        _build_rewriter,
        _build_minutes_synthesizer,
        _build_discussions_synthesizer,
        _build_notes_extractor,
        _build_generic_pipeline,
        _build_map_reduce_section,
        _build_init_then_refine_section,
        _build_g_eval_scorer,
    ],
)
def test_every_llm_client_waits_the_full_gateway_hour(
    build: Callable[[], object],
) -> None:
    OpenAI.reset_mock()
    AsyncOpenAI.reset_mock()

    build()

    calls = OpenAI.call_args_list + AsyncOpenAI.call_args_list
    assert calls, "the service built no OpenAI client"
    for call in calls:
        assert call.kwargs["timeout"] == GATEWAY_TIMEOUT_SECONDS
