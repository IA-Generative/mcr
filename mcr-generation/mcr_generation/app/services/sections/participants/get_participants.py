import re

from loguru import logger

from mcr_generation.app.schemas.base import Participant, Participants
from mcr_generation.app.services.utils.input_chunker import Chunk

MAX_NAME_WORDS = 6  # This values is arbitrary
LETTER_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")


def _extract_name_candidate(line: str) -> str | None:
    if ":" not in line:
        return None

    candidate = line.split(":", 1)[0].strip(" -\t")
    if not candidate:
        return None

    words = [word for word in candidate.split() if word]
    if len(words) == 0 or len(words) > MAX_NAME_WORDS:
        return None

    # Avoid keeping prefixes like timestamps that contain no letter (e.g. 09:30, ---, timestamps)
    if LETTER_PATTERN.search(candidate) is None:
        return None

    return " ".join(words)


def _extract_unique_names_in_order(chunks: list[Chunk]) -> list[str]:
    names_in_order: list[str] = []
    seen_names: set[str] = set()

    for chunk in chunks:
        for line in chunk.text.splitlines():
            name = _extract_name_candidate(line.strip())
            if name is None or name in seen_names:
                continue
            seen_names.add(name)
            names_in_order.append(name)

    return names_in_order


def get_participants_from_chunks(chunks: list[Chunk]) -> Participants:
    names_in_order = _extract_unique_names_in_order(chunks)

    logger.info("Extracted participant names in order: {}", names_in_order)

    participants = [
        Participant(
            speaker_id=f"LOCUTEUR_{idx:02d}",
            name=name,
            role=None,
            confidence=None,
            association_justification=None,
        )
        for idx, name in enumerate(names_in_order)
    ]
    return Participants(participants=participants)
