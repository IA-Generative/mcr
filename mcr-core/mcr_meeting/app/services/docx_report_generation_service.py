from io import BytesIO
from typing import Any, Optional

from docxtpl import RichText

from mcr_meeting.app.schemas.report_generation import (
    ReportGenerationResponse,
    ReportHeader,
    ReportParticipant,
)
from mcr_meeting.app.services.docx_generation.templated_docx_generator import (
    TemplatedDocxGenerator,
)


def generate_docx_decisions_reports_from_template(
    response: ReportGenerationResponse, meeting_name: Optional[str]
) -> BytesIO:
    """
    Generates a DOCX decision report from a predefined template and replaces placeholders with meeting data.

    Args:
        participants (list): A list of participants in the meeting.
        decisions_json (ReportGenerationResponse): The decisions data in JSON format.
        meeting_name (str): The name of the meeting.

    Returns:
        BytesIO: A BytesIO object containing the generated DOCX document.

    Raises:
        FileNotFoundError: If the DOCX template file is not found.
    """
    doc_generator = ReportDocxGenerator("FCR_report_template.docx")

    header = response.header
    title = format_title_for_report(header, meeting_name)
    participants = header.participants if header is not None else []

    doc_generator.fill_templated_doc(
        decisions_json=response,
        meeting_name=title,
        participants=participants,
        objective=header.objective if header else None,
        next_meeting=header.next_meeting if header else None,
    )
    return doc_generator.save_and_return_docx()


class ReportDocxGenerator(TemplatedDocxGenerator):
    """
    Renders the FCR report template using docxtpl.
    Template placeholders:
      - {{meeting_name}}
      - {{objective}}
      - {{participants}}
      - {{decisions}}
      - {{next_steps}}
    """

    def __init__(self, filename: str):
        super().__init__(filename)

    def fill_templated_doc(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[explicit-any]
        """
        High-level API: build context, render, and return BytesIO.
        """
        context = self.build_context(*args, **kwargs)
        self.doc.render(context)

    def build_context(
        self,
        meeting_name: str,
        objective: Optional[str],
        next_meeting: Optional[str],
        decisions_json: ReportGenerationResponse,
        participants: list[ReportParticipant],
    ) -> dict[str, str | RichText]:
        objective_text = objective if objective else "Non spécifié."

        return {
            "meeting_name": meeting_name,
            "objective": objective_text,
            "next_meeting": next_meeting if next_meeting else "",
            "participants": self.build_participants_context_text(participants),
            "decisions": self.build_decisions_context_richtext(decisions_json),
            "next_steps": decisions_json.next_steps,
        }

    def build_participants_context_text(
        self,
        participants: list[ReportParticipant],
    ) -> str:
        sorted_participants = sorted(
            participants or [], key=lambda p: p.confidence or 0, reverse=True
        )

        participants_lines: list[str] = []
        for p in sorted_participants:
            naming = p.name if p.name else p.speaker_id
            if p.role:
                participants_lines.append(f"    - {naming} ({p.role})")
            else:
                participants_lines.append(f"    - {naming}")

        participants_text = "\n".join(participants_lines) if participants_lines else ""

        return participants_text

    def build_decisions_context_richtext(
        self,
        decisions_json: ReportGenerationResponse,
    ) -> RichText:
        """
        Build decisions context as RichText for DOCX report.
        """
        rt = RichText()
        for index, topic in enumerate(decisions_json.topics_with_decision):
            is_last_topic = index == len(decisions_json.topics_with_decision) - 1
            rt.add(topic.title, bold=True)
            rt.add("\n")
            if topic.introduction_text:
                rt.add(topic.introduction_text)
                rt.add("\n")
            if topic.details:
                for detail in topic.details:
                    rt.add("    - " + detail)
                    rt.add("\n")

            if topic.main_decision:
                rt.add("=> " + topic.main_decision, italic=True)
                if is_last_topic:
                    continue
                rt.add("\n")

            # Add an extra line break between topics but not after the last one
            if is_last_topic:
                continue

            rt.add("\n")

        return rt


def format_title_for_report(
    header: Optional[ReportHeader], meeting_name: Optional[str]
) -> str:
    return "Compte-rendu " + (
        header.title
        if header is not None and header.title is not None
        else meeting_name
        if meeting_name is not None
        else ""
    )
