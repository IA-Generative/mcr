"""Unit tests for RefineIntent's notes-authority behaviour.

Bug 1 of the "notes biaisent l'objectif" ticket: when the intent seed comes from
the user's notes, the header refine must let the notes win against a contradicting
transcript chunk (symmetry with the reduce's NOTES_SECTION_TEMPLATE). When the
seed is extracted from a transcript chunk instead, no such precedence applies.

``tests/conftest.py`` replaces the ``refine_intent`` module with a MagicMock (its
package __init__ chain would otherwise pull in leaves that init a real LLM client).
Evict it and re-import so we bind to the *real* ``RefineIntent`` class — not a
mirror — and so a regression in its own wiring (e.g. dropping the authority clause
binding) is actually caught here.
"""

import importlib
import sys
from collections.abc import Callable
from typing import Any

from mcr_generation.app.schemas.base import Intent
from mcr_generation.app.services.sections.intent.prompts import (
    REFINE_NOTES_AUTHORITY_CLAUSE,
)
from mcr_generation.app.services.utils.input_chunker import Chunk

sys.modules.pop("mcr_generation.app.services.sections.intent.refine_intent", None)
_refine_intent_module = importlib.import_module(
    "mcr_generation.app.services.sections.intent.refine_intent"
)
RefineIntent = _refine_intent_module.RefineIntent

# The base mechanism (init_then_refine) is where the LLM call is patched.
_MODULE_PATH = "mcr_generation.app.services.sections.base.init_then_refine"


def _intent(title: str) -> Intent:
    return Intent(title=title, objective=title, confidence=0.9, justification="x")


class TestRefineIntentNotesAuthority:
    def test_clause_is_non_empty_and_names_the_notes_precedence(self) -> None:
        assert REFINE_NOTES_AUTHORITY_CLAUSE.strip()
        assert "notes" in REFINE_NOTES_AUTHORITY_CLAUSE.lower()

    def test_refine_prompt_exposes_the_notes_authority_slot(self) -> None:
        # Without the slot in the real template, the clause could never be
        # injected — the two behaviours below would pass vacuously.
        assert "{notes_authority}" in RefineIntent.refine_prompt_template

    def test_notes_seeded_refine_tells_the_llm_notes_take_precedence(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        seed_from_notes = _intent("Démo repoussée au 14/10")

        with fake_call_llm_with_structured_output(
            _MODULE_PATH, _intent("après refine")
        ) as mock_call:
            RefineIntent().init_then_refine(
                [Chunk(id=0, text="la démo aura lieu le 30 septembre")],
                init_hint=seed_from_notes,
            )

        content = mock_call.call_args.kwargs["user_message_content"]
        assert REFINE_NOTES_AUTHORITY_CLAUSE in content

    def test_chunk_seeded_refine_has_no_notes_precedence(
        self,
        fake_call_llm_with_structured_output: Callable[..., Any],
    ) -> None:
        responses = [_intent("depuis chunk 0"), _intent("depuis chunk 1")]

        with fake_call_llm_with_structured_output(_MODULE_PATH, responses) as mock_call:
            RefineIntent().init_then_refine(
                [
                    Chunk(id=0, text="premier extrait"),
                    Chunk(id=1, text="second extrait"),
                ]
            )

        refine_content = mock_call.call_args_list[-1].kwargs["user_message_content"]
        assert REFINE_NOTES_AUTHORITY_CLAUSE not in refine_content
