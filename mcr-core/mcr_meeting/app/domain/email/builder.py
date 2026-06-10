from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from mcr_meeting.app.configs.base import Settings

templates_dir = Path(__file__).parent / "registry"
templates_env = Environment(
    loader=FileSystemLoader(templates_dir),
)

settings = Settings()


@dataclass(frozen=True)
class EmailContent:
    subject: str
    html: str


def build_transcription_ready_email(meeting_name: str, meeting_id: int) -> EmailContent:
    meeting_link = _build_meeting_link(meeting_id)
    return EmailContent(
        subject=f"Votre transcription de la réunion {meeting_name} est prête",
        html=_render_transcription_generation_success(
            meeting_name=meeting_name, meeting_link=meeting_link
        ),
    )


def build_report_ready_email(meeting_name: str, meeting_id: int) -> EmailContent:
    meeting_link = _build_meeting_link(meeting_id)
    return EmailContent(
        subject=f"Votre compte-rendu de la réunion {meeting_name} est prêt",
        html=_render_report_generation_success(
            meeting_name=meeting_name, meeting_link=meeting_link
        ),
    )


def _build_meeting_link(meeting_id: int) -> str:
    return f"{settings.MCR_FRONTEND_URL}/meetings/{meeting_id}"


def _render_transcription_generation_success(
    meeting_name: str,
    meeting_link: str,
) -> str:
    template = templates_env.get_template("transcription_generation_success.html")
    return template.render(meeting_name=meeting_name, meeting_link=meeting_link)


def _render_report_generation_success(
    meeting_name: str,
    meeting_link: str,
) -> str:
    template = templates_env.get_template("report_generation_success.html")
    return template.render(meeting_name=meeting_name, meeting_link=meeting_link)
