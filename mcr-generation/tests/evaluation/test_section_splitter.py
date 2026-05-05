import pytest

from mcr_generation.evaluation.pipeline.section_splitter import extract_section

SAMPLE_REPORT = """\
# Réunion daily

**Objectif** : alignement de l'équipe

## Participants

- Alice — PO
- Bob — Tech Lead

## Topics

### Migration cloud

Préparer la migration des services backend.
- Audit des dépendances
- Plan de cutover

## Next steps

- Alice prépare l'audit
- Bob valide le plan

## Prochaine réunion

mardi prochain
"""


class TestExtractSection:
    def test_extracts_topics_block(self) -> None:
        body = extract_section(SAMPLE_REPORT, "topics")
        assert body is not None
        assert "Migration cloud" in body
        assert "Plan de cutover" in body
        # Must stop before the next `## ` heading.
        assert "Alice prépare l'audit" not in body

    def test_extracts_participants_block(self) -> None:
        body = extract_section(SAMPLE_REPORT, "participants")
        assert body is not None
        assert "Alice" in body
        assert "Bob" in body
        assert "Migration cloud" not in body

    def test_extracts_next_steps_block(self) -> None:
        body = extract_section(SAMPLE_REPORT, "next_steps")
        assert body is not None
        assert "Alice prépare l'audit" in body
        assert "Bob valide le plan" in body
        assert "mardi prochain" not in body

    def test_returns_none_when_section_is_absent(self) -> None:
        report_without_topics = "## Participants\n- Alice\n"
        assert extract_section(report_without_topics, "topics") is None

    def test_unknown_section_name_raises(self) -> None:
        with pytest.raises(KeyError):
            extract_section(SAMPLE_REPORT, "unknown_section")
