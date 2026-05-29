"""Unit tests for the participants prompt helpers."""

from mcr_generation.app.schemas.base import ParticipantHint, ParticipantsHint
from mcr_generation.app.services.sections.participants.prompts import (
    render_participants_hint,
)


def test_render_participants_hint_bullets_with_and_without_role() -> None:
    block = render_participants_hint(
        ParticipantsHint(
            participants=[
                ParticipantHint(name="Marie", role="Directrice financière"),
                ParticipantHint(name="Pierre"),
            ]
        )
    )
    assert block == "- Marie (Directrice financière)\n- Pierre"


def test_render_participants_hint_falls_back_when_absent_or_empty() -> None:
    assert "Aucune note" in render_participants_hint(None)
    assert "Aucune note" in render_participants_hint(ParticipantsHint(participants=[]))
