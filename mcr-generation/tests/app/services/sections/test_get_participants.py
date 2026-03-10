import pytest

from mcr_generation.app.services.sections.participants.get_participants import (
    _extract_name_candidate,
    get_participants_from_chunks,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


@pytest.mark.parametrize(
    ("line", "expected_name"),
    [
        ("Alice Martin: Bonjour", "Alice Martin"),
        ("  -\t Jean Dupont : Salut", "Jean Dupont"),
        ("A B C D E F  : ok", "A B C D E F"),
        ("LOCUTEUR_00 : Salut", "LOCUTEUR_00"),
    ],
)
def test_extract_name_candidate_returns_normalized_name(
    line: str, expected_name: str
) -> None:
    assert _extract_name_candidate(line) == expected_name


@pytest.mark.parametrize(
    "line",
    [
        "No speaker prefix",
        "    : message",
        "A B C D E F G: too many words",
        "---: separator",
        "09:30: ouverture",
    ],
)
def test_extract_name_candidate_rejects_invalid_candidates(line: str) -> None:
    assert _extract_name_candidate(line) is None


def test_extracts_name_before_first_colon_with_max_six_words() -> None:
    chunks = [
        Chunk(id=0, text="Alice Martin: Bonjour a tous\nLOCUTEUR_01: point"),
        Chunk(id=1, text="Jean Dupont: Merci"),
    ]

    participants = get_participants_from_chunks(chunks)

    assert [participant.name for participant in participants.participants] == [
        "Alice Martin",
        "LOCUTEUR_01",
        "Jean Dupont",
    ]


def test_deduplicates_names_while_preserving_first_seen_order() -> None:
    chunks = [
        Chunk(id=0, text="Alice Martin: Bonjour"),
        Chunk(id=1, text="Jean Dupont: Merci\nAlice Martin: Rebonjour"),
    ]

    participants = get_participants_from_chunks(chunks)

    assert [participant.name for participant in participants.participants] == [
        "Alice Martin",
        "Jean Dupont",
    ]


def test_ignores_prefix_without_letters() -> None:
    chunks = [Chunk(id=0, text="09:30: ouverture\nPierre: salut")]

    participants = get_participants_from_chunks(chunks)

    assert [participant.name for participant in participants.participants] == ["Pierre"]
