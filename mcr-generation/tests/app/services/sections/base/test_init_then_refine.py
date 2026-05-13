from collections.abc import Callable
from typing import Any

import langfuse
from pydantic import BaseModel

from mcr_generation.app.services.sections.base.init_then_refine import (
    BaseInitThenRefine,
)
from mcr_generation.app.services.utils.input_chunker import Chunk

_MODULE_PATH = "mcr_generation.app.services.sections.base.init_then_refine"


class _StubModel(BaseModel):
    text: str


class _StubRefiner(BaseInitThenRefine[_StubModel]):
    response_model = _StubModel
    initial_prompt_template = "INITIAL: {chunk_text}"
    refine_prompt_template = "REFINE: {current_json} | {chunk_text}"
    section_name = "stub"


class TestInitialExtract:
    def test_initial_extract_uses_initial_template_and_response_model(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        expected = _StubModel(text="seed")

        with fake_call_llm_with_structured_output(_MODULE_PATH, expected) as mock_call:
            refiner = _StubRefiner()
            result = refiner._initial_extract_from_chunk(Chunk(id=0, text="hello"))

        assert result == expected
        mock_call.assert_called_once()
        kwargs = mock_call.call_args.kwargs
        assert kwargs["response_model"] is _StubModel
        assert kwargs["user_message_content"] == "INITIAL: hello"


class TestRefineWithChunk:
    def test_refine_uses_refine_template_with_current_json(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        current = _StubModel(text="prev")
        expected = _StubModel(text="next")

        with fake_call_llm_with_structured_output(_MODULE_PATH, expected) as mock_call:
            refiner = _StubRefiner()
            result = refiner._refine_with_chunk(current=current, chunk_text="more")

        assert result == expected
        mock_call.assert_called_once()
        kwargs = mock_call.call_args.kwargs
        assert kwargs["response_model"] is _StubModel
        content = kwargs["user_message_content"]
        assert content.startswith("REFINE: ")
        assert current.model_dump_json() in content
        assert "more" in content


class TestInitThenRefineLoop:
    def test_one_chunk_returns_initial_only(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        initial = _StubModel(text="only")

        with fake_call_llm_with_structured_output(_MODULE_PATH, initial) as mock_call:
            refiner = _StubRefiner()
            result = refiner.init_then_refine([Chunk(id=0, text="c0")])

        assert result == initial
        assert mock_call.call_count == 1

    def test_n_chunks_does_init_plus_n_minus_one_refines(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        responses = [
            _StubModel(text="s0"),
            _StubModel(text="s1"),
            _StubModel(text="s2"),
        ]

        with fake_call_llm_with_structured_output(_MODULE_PATH, responses) as mock_call:
            refiner = _StubRefiner()
            refiner.init_then_refine(
                [
                    Chunk(id=0, text="c0"),
                    Chunk(id=1, text="c1"),
                    Chunk(id=2, text="c2"),
                ]
            )

        assert mock_call.call_count == 3

    def test_returns_last_refined_value(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        responses = [
            _StubModel(text="s0"),
            _StubModel(text="s1"),
            _StubModel(text="s2_final"),
        ]

        with fake_call_llm_with_structured_output(_MODULE_PATH, responses):
            refiner = _StubRefiner()
            result = refiner.init_then_refine(
                [
                    Chunk(id=0, text="c0"),
                    Chunk(id=1, text="c1"),
                    Chunk(id=2, text="c2"),
                ]
            )

        assert result == responses[-1]


class TestInitThenRefineWithHint:
    def test_hint_skips_initial_extract_and_refines_every_chunk(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        hint = _StubModel(text="from-notes")
        responses = [_StubModel(text="r0"), _StubModel(text="r1")]

        with fake_call_llm_with_structured_output(_MODULE_PATH, responses) as mock_call:
            refiner = _StubRefiner()
            refiner.init_then_refine(
                [Chunk(id=0, text="c0"), Chunk(id=1, text="c1")],
                init_hint=hint,
            )

        assert mock_call.call_count == 2
        for call in mock_call.call_args_list:
            content = call.kwargs["user_message_content"]
            assert content.startswith("REFINE: ")

    def test_first_refine_uses_hint_as_current_json(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        hint = _StubModel(text="seed-from-notes")
        refined = _StubModel(text="after-refine")

        with fake_call_llm_with_structured_output(_MODULE_PATH, refined) as mock_call:
            refiner = _StubRefiner()
            refiner.init_then_refine([Chunk(id=0, text="c0")], init_hint=hint)

        assert mock_call.call_count == 1
        content = mock_call.call_args.kwargs["user_message_content"]
        assert content.startswith("REFINE: ")
        assert hint.model_dump_json() in content
        assert "c0" in content


class TestLangfuseSpanRename:
    def test_init_then_refine_renames_langfuse_span(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        langfuse_client = langfuse.get_client.return_value
        langfuse_client.reset_mock()

        with fake_call_llm_with_structured_output(_MODULE_PATH, _StubModel(text="x")):
            refiner = _StubRefiner()
            refiner.init_then_refine([Chunk(id=0, text="hello")])

        langfuse_client.update_current_span.assert_called_once_with(
            name="section_stub_generation"
        )
