from io import BytesIO

from mcr_meeting.app.configs.base import S3Settings
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.services.s3_service import (
    get_report_object_name,
    put_file_to_s3,
)
from mcr_meeting.app.utils.file_validation import DOCX_MIME_TYPE

s3_settings = S3Settings()


def get_transcription_object_name(meeting_id: int, filename: str) -> str:
    return f"{s3_settings.S3_TRANSCRIPTION_FOLDER}/{meeting_id}/{filename}"


def upload_report_to_s3(
    meeting_id: int,
    deliverable_type: DeliverableType,
    content: BytesIO,
) -> str:
    object_name = _object_name_for_deliverable(meeting_id, deliverable_type)
    put_file_to_s3(
        content=content,
        object_name=object_name,
        content_type=DOCX_MIME_TYPE,
    )
    return object_name


def _object_name_for_deliverable(
    meeting_id: int, deliverable_type: DeliverableType
) -> str:
    filename = f"{deliverable_type.lower()}.docx"
    return get_report_object_name(meeting_id=meeting_id, filename=filename)
