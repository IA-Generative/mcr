from io import BytesIO

from mcr_meeting.app.exceptions.exceptions import MCRException
from mcr_meeting.app.schemas.report_generation import (
    ReportResponse,
    is_custom_report,
    is_decision_report_synthesis,
    is_detailed_synthesis,
)
from mcr_meeting.app.services.docx_report_generation_service import (
    generate_custom_report_docx,
    generate_detailed_synthesis_docx,
    generate_docx_decisions_reports_from_template,
)


def render_report(report_response: ReportResponse, meeting_name: str) -> BytesIO:
    if is_detailed_synthesis(report_response):
        return generate_detailed_synthesis_docx(report_response, meeting_name)
    if is_decision_report_synthesis(report_response):
        return generate_docx_decisions_reports_from_template(
            report_response, meeting_name
        )
    if is_custom_report(report_response):
        return generate_custom_report_docx(report_response)
    raise MCRException("Invalid report_response type")
