from pathlib import Path

from jinja2 import Environment, FileSystemLoader

templates_dir = Path(__file__).parent / "registry"
templates_env = Environment(
    loader=FileSystemLoader(templates_dir),
)


def get_transcription_generation_success_email_template(
    meeting_name: str,
    meeting_link: str,
) -> str:
    template = templates_env.get_template("transcription_generation_success.html")
    return template.render(meeting_name=meeting_name, meeting_link=meeting_link)


def get_report_generation_success_email_template(
    meeting_name: str,
    meeting_link: str,
) -> str:
    template = templates_env.get_template("report_generation_success.html")
    return template.render(meeting_name=meeting_name, meeting_link=meeting_link)
