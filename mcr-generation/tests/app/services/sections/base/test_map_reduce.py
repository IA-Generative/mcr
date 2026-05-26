"""Unit tests for BaseMapReduce via a minimal stub subclass."""

from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field

from mcr_generation.app.exceptions.exceptions import AllChunksFailedError
from mcr_generation.app.services.sections.base.map_reduce import BaseMapReduce
from mcr_generation.app.services.sections.detailed_discussions.types import (
    MappedDetailedDiscussionsLLM,
)
from mcr_generation.app.services.sections.topics.types import MappedTopicsLLM
from mcr_generation.app.services.utils.input_chunker import Chunk

_MODULE_PATH = "mcr_generation.app.services.sections.base.map_reduce"


class _StubMappedLLM(BaseModel):
    topic: str
    topic_confidence: float
    payload: str = ""


class _StubMapped(_StubMappedLLM):
    chunk_id: int


class _StubMapResp(BaseModel):
    items: list[_StubMappedLLM] = Field(default_factory=list)


class _StubContent(BaseModel):
    items: list[_StubMapped] = Field(default_factory=list)


class _StubMapReduce(BaseMapReduce[_StubMapped, _StubContent]):
    section_name = "stub"
    map_response_model = _StubMapResp
    item_model = _StubMapped
    content_model = _StubContent
    map_prompt_template = "MAP {chunk_text} | {meeting_subject} | {speaker_mapping}"
    reduce_prompt_template = (
        "REDUCE {items} | {meeting_subject} | {speaker_mapping}{notes_section}"
    )
    items_field = "items"


def _build_hint(topic: str = "from-notes") -> _StubContent:
    return _StubContent(
        items=[_StubMapped(topic=topic, topic_confidence=0.9, chunk_id=0)]
    )


class TestOrchestrationAndChunkIdProvenance:
    def test_map_reduce_runs_map_then_reduce_and_stamps_chunk_id(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        """End-to-end via map_reduce_all_steps. The LLM produces items
        without a chunk_id (it's not part of the LLM-facing schema); the
        base stamps each item with the chunk.id of the chunk it came from."""
        map_resp_a = _StubMapResp(
            items=[_StubMappedLLM(topic="A", topic_confidence=0.9)]
        )
        map_resp_b = _StubMapResp(
            items=[_StubMappedLLM(topic="B", topic_confidence=0.9)]
        )
        reduce_resp = _StubContent(
            items=[_StubMapped(topic="X-reduced", topic_confidence=0.9, chunk_id=0)]
        )

        with fake_call_llm_with_structured_output(
            _MODULE_PATH, [map_resp_a, map_resp_b, reduce_resp]
        ) as mock_call:
            mr = _StubMapReduce()
            result = mr.map_reduce_all_steps(
                [Chunk(id=7, text="c7"), Chunk(id=13, text="c13")]
            )

        assert result == reduce_resp
        assert mock_call.call_count == 3

        reduce_prompt = mock_call.call_args_list[-1].kwargs["user_message_content"]
        assert "'chunk_id': 7" in reduce_prompt
        assert "'chunk_id': 13" in reduce_prompt


class TestNotesHintInjection:
    @pytest.mark.parametrize(
        ("hint", "expect_block"),
        [(None, False), (_build_hint(), True)],
    )
    def test_reduce_injects_notes_block_only_when_hint_provided(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
        hint: _StubContent | None,
        expect_block: bool,
    ) -> None:
        items = [_StubMapped(topic="X", topic_confidence=0.9, chunk_id=0)]

        with fake_call_llm_with_structured_output(
            _MODULE_PATH, _StubContent()
        ) as mock_call:
            _StubMapReduce()._reduce(items, notes_hint=hint)

        prompt = mock_call.call_args.kwargs["user_message_content"]
        if expect_block:
            assert "## Notes du rédacteur" in prompt
            assert "### Comment utiliser ces notes" in prompt
            assert hint.model_dump_json() in prompt  # type: ignore[union-attr]
        else:
            assert "Notes du rédacteur" not in prompt


class TestReduceEmptyShortCircuit:
    @pytest.mark.parametrize("hint", [None, _build_hint()])
    def test_short_circuits_without_llm_call(
        self,
        hint: _StubContent | None,
    ) -> None:
        with (
            patch(f"{_MODULE_PATH}.call_llm_with_structured_output") as mock_call,
            patch(f"{_MODULE_PATH}.record_empty_map_phase_event") as mock_event,
            patch(f"{_MODULE_PATH}.logger") as mock_logger,
        ):
            result = _StubMapReduce()._reduce([], notes_hint=hint)

        assert result == _StubContent()
        mock_call.assert_not_called()
        mock_event.assert_called_once_with(
            section="stub",
            chunk_count=None,
            notes_hint_present=hint is not None,
        )
        mock_logger.warning.assert_called_once()


class TestMapPhaseFailures:
    def test_partial_failure_records_event_and_keeps_succeeded_items(
        self,
    ) -> None:
        good_chunk = Chunk(id=0, text="ok")
        bad_chunk = Chunk(id=1, text="boom")

        def fake_map_extract(self: Any, chunk: Chunk) -> list[_StubMapped]:  # noqa: ANN401
            if chunk.id == bad_chunk.id:
                raise RuntimeError("boom")
            return [_StubMapped(topic="X", topic_confidence=0.9, chunk_id=chunk.id)]

        with (
            patch.object(_StubMapReduce, "_map_extract", fake_map_extract),
            patch(f"{_MODULE_PATH}.record_chunk_map_failed_event") as mock_failed_event,
            patch(f"{_MODULE_PATH}.call_llm_with_structured_output") as mock_call,
        ):
            mock_call.return_value = _StubContent()
            _StubMapReduce().map_reduce_all_steps([good_chunk, bad_chunk])

        mock_failed_event.assert_called_once()
        kwargs = mock_failed_event.call_args.kwargs
        assert kwargs["section"] == "stub"
        assert kwargs["chunk_id"] == bad_chunk.id
        assert kwargs["exception_type"] == "RuntimeError"
        mock_call.assert_called_once()

    def test_all_chunks_fail_raises_all_chunks_failed_error(self) -> None:
        def always_fail(self: Any, chunk: Chunk) -> list[_StubMapped]:  # noqa: ANN401
            raise RuntimeError("boom")

        with (
            patch.object(_StubMapReduce, "_map_extract", always_fail),
            patch(f"{_MODULE_PATH}.record_chunk_map_failed_event"),
        ):
            with pytest.raises(AllChunksFailedError):
                _StubMapReduce().map_reduce_all_steps(
                    [Chunk(id=0, text="a"), Chunk(id=1, text="b")]
                )


class TestLLMSchemaCleanliness:
    """Verifies that chunk_id, which is an internal-only field, is not
    exposed to the LLM through the JSON schema generated for the map
    response model (the wrapper Instructor sends to the LLM)."""

    @pytest.mark.parametrize(
        ("wrapper_cls", "item_def_name"),
        [
            (MappedTopicsLLM, "MappedTopicLLM"),
            (MappedDetailedDiscussionsLLM, "MappedDetailedDiscussionLLM"),
        ],
    )
    def test_chunk_id_absent_from_item_schema(
        self,
        wrapper_cls: type[BaseModel],
        item_def_name: str,
    ) -> None:
        schema = wrapper_cls.model_json_schema()
        item_schema = schema["$defs"][item_def_name]
        assert "chunk_id" not in item_schema.get("properties", {})
        assert "chunk_id" not in item_schema.get("required", [])
