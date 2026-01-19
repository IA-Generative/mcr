from io import BytesIO
from typing import BinaryIO, Optional

from mcr_meeting.app.exceptions.exceptions import (
    NotFoundException,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.services.meeting_service import set_meeting_report_filename
from mcr_meeting.app.services.s3_service import (
    get_file_from_s3,
    get_report_object_name,
    put_file_to_s3,
)
from mcr_meeting.app.utils.files_mime_types import DOCX_MIME_TYPE

DEFAULT_REPORT_FILENAME = "report.docx"


def get_formatted_report_from_s3(meeting: Meeting) -> BytesIO:
    if meeting.report_filename is None:
        raise NotFoundException(
            "Couldn't get report as meeting.report_filename is empty"
        )
    object_name = get_report_object_name(
        meeting_id=meeting.id, filename=meeting.report_filename
    )
    return get_file_from_s3(object_name)


def save_formatted_report(
    meeting_id: int, file_like_object: BinaryIO, filename: Optional[str] = None
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
