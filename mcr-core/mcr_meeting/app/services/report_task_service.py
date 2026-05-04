from io import BytesIO
from typing import BinaryIO

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.exceptions.exceptions import (
    MCRException,
    NotFoundException,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.schemas.report_generation import (
    ReportResponse,
    is_decision_report_synthesis,
    is_detailed_synthesis,
)
from mcr_meeting.app.services.docx_report_generation_service import (
    generate_detailed_synthesis_docx,
    generate_docx_decisions_reports_from_template,
)
from mcr_meeting.app.services.meeting_service import set_meeting_report_filename
from mcr_meeting.app.services.s3_service import (
    get_file_from_s3,
    get_file_from_s3_or_none,
    get_report_object_name,
    put_file_to_s3,
)
from mcr_meeting.app.utils.file_validation import DOCX_MIME_TYPE

DEFAULT_REPORT_FILENAME = "report.docx"


def deliverable_object_filename(deliverable_type: DeliverableType) -> str:
    return f"{deliverable_type.value.lower()}.docx"


def get_formatted_report_from_s3(meeting: Meeting) -> BytesIO:
    if meeting.report_filename is None:
        raise NotFoundException(
            "Couldn't get report as meeting.report_filename is empty"
        )
    object_name = get_report_object_name(
        meeting_id=meeting.id, filename=meeting.report_filename
    )
    return get_file_from_s3(object_name)


def get_typed_deliverable_from_s3(
    meeting: Meeting, deliverable_type: DeliverableType
) -> BytesIO | None:
    object_name = get_report_object_name(
        meeting_id=meeting.id,
        filename=deliverable_object_filename(deliverable_type),
    )
    return get_file_from_s3_or_none(object_name)


def save_formatted_report(
    meeting_id: int, file_like_object: BinaryIO, filename: str | None = None
) -> None:
    name = filename if filename is not None else DEFAULT_REPORT_FILENAME

    content = BytesIO(file_like_object.read())
    file_like_object.seek(0)
    object_name = get_report_object_name(meeting_id=meeting_id, filename=name)
    put_file_to_s3(
        content=content, object_name=object_name, content_type=DOCX_MIME_TYPE
    )

    set_meeting_report_filename(
        meeting_id=meeting_id,
        filename=name,
    )


def persist_report_docx(meeting_id: int, report_response: ReportResponse) -> None:
    meeting = get_meeting_by_id(meeting_id=meeting_id)
    if is_detailed_synthesis(report_response):
        docx_buffer = generate_detailed_synthesis_docx(report_response, meeting.name)
        deliverable_type = DeliverableType.DETAILED_SYNTHESIS
    elif is_decision_report_synthesis(report_response):
        docx_buffer = generate_docx_decisions_reports_from_template(
            report_response, meeting.name
        )
        deliverable_type = DeliverableType.DECISION_RECORD
    else:
        raise MCRException("Invalid report_response type")

    save_formatted_report(
        meeting_id=meeting_id,
        file_like_object=docx_buffer,
        filename=deliverable_object_filename(deliverable_type),
    )
