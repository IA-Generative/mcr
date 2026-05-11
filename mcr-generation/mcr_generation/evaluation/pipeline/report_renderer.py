"""Render a generated `BaseReport` into markdown for evaluation.

The rendered markdown uses `## ` section headings whose text is mirrored in
`section_splitter.SECTION_HEADERS`, so that section-scoped criteria can extract
the right block.
"""

from mcr_generation.app.schemas.base import (
    BaseReport,
    DecisionRecord,
    DetailedSynthesis,
    Header,
    Participant,
    Topic,
)


def render_report(report: BaseReport) -> str:
    if isinstance(report, DecisionRecord):
        return _render_decision_record(report)
    if isinstance(report, DetailedSynthesis):
        return _render_detailed_synthesis(report)
    raise TypeError(f"Unsupported report type: {type(report).__name__}")


def _render_header(header: Header) -> list[str]:
    lines: list[str] = []
    if header.title:
        lines.append(f"# {header.title}")
    if header.objective:
        lines.append("")
        lines.append(f"**Objectif** : {header.objective}")
    return lines


def _render_participants(participants: list[Participant]) -> list[str]:
    lines = ["## Participants", ""]
    if not participants:
        lines.append("(aucun participant identifié)")
        return lines
    for p in participants:
        name = p.name or p.speaker_id
        if p.role:
            lines.append(f"- {name} — {p.role}")
        else:
            lines.append(f"- {name}")
    return lines


def _render_topics(topics: list[Topic]) -> list[str]:
    lines = ["## Topics", ""]
    if not topics:
        lines.append("(aucun topic)")
        return lines
    for topic in topics:
        lines.append(f"### {topic.title}")
        if topic.introduction_text:
            lines.append(topic.introduction_text)
        for detail in topic.details:
            lines.append(f"- {detail}")
        if topic.main_decision:
            lines.append(f"**Décision** : {topic.main_decision}")
        lines.append("")
    return lines


def _render_next_steps(next_steps: list[str]) -> list[str]:
    lines = ["## Next steps", ""]
    if not next_steps:
        lines.append("(aucun next step)")
        return lines
    lines.extend(f"- {step}" for step in next_steps)
    return lines


def _render_next_meeting(next_meeting: str | None) -> list[str]:
    if not next_meeting:
        return []
    return ["## Prochaine réunion", "", next_meeting]


def _join(blocks: list[list[str]]) -> str:
    return "\n".join("\n".join(block) for block in blocks if block).strip() + "\n"


def _render_decision_record(report: DecisionRecord) -> str:
    return _join(
        [
            _render_header(report.header),
            _render_participants(report.header.participants),
            _render_topics(report.topics_with_decision),
            _render_next_steps(report.next_steps),
            _render_next_meeting(report.header.next_meeting),
        ]
    )


def _render_detailed_synthesis(report: DetailedSynthesis) -> str:
    discussion_lines = ["## Topics", ""]
    for d in report.detailed_discussions:
        discussion_lines.append(f"### {d.title}")
        for k in d.key_ideas:
            discussion_lines.append(f"- {k}")
        for decision in d.decisions:
            discussion_lines.append(f"**Décision** : {decision}")
        for action in d.actions:
            discussion_lines.append(f"**Action** : {action}")
        discussion_lines.append("")

    summary_block: list[str] = []
    if report.discussions_summary:
        summary_block = ["## Synthèse", ""]
        summary_block.extend(f"- {s}" for s in report.discussions_summary)

    return _join(
        [
            _render_header(report.header),
            _render_participants(report.header.participants),
            summary_block,
            discussion_lines,
            ["## Next steps", "", *(f"- {item}" for item in report.to_do_list)]
            if report.to_do_list
            else ["## Next steps", "", "(aucun next step)"],
            _render_next_meeting(report.header.next_meeting),
        ]
    )
