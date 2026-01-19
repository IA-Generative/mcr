from io import BytesIO
from typing import BinaryIO, Optional

from loguru import logger

from mcr_meeting.app.exceptions.exceptions import (
    NotFoundException,
    TaskCreationException,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.schemas.celery_types import MCRTranscriptionTasks
from mcr_meeting.app.services.docx_transcription_generation_service import (
    generate_transcription_docx,
)
from mcr_meeting.app.services.meeting_service import (
    set_meeting_transcription_filename_and_update_status,
)
from mcr_meeting.app.services.s3_service import (
    get_file_from_s3,
    get_transcription_object_name,
    put_file_to_s3,
)
from mcr_meeting.app.utils.celery_producer import celery_producer_app
from mcr_meeting.app.utils.files_mime_types import DOCX_MIME_TYPE

DEFAULT_TRANSCRIPTION_FILENAME = "transcription.docx"


async def retrieve_or_create_formatted_docx_transcription(meeting: Meeting) -> BytesIO:
    if meeting.transcription_filename is None:
        docx_buffer = create_formatted_docx_transcription(meeting)
    else:
        docx_buffer = get_formatted_transcription_from_s3(meeting)

    return docx_buffer


def get_formatted_transcription_from_s3(meeting: Meeting) -> BytesIO:
    if meeting.transcription_filename is None:
        raise NotFoundException(
            "Couldn't get transcription as meeting.transcription_filename is empty"
        )
    object_name = get_transcription_object_name(
        meeting_id=meeting.id, filename=meeting.transcription_filename
    )
    return get_file_from_s3(object_name)


def create_formatted_docx_transcription(meeting: Meeting) -> BytesIO:
    docx_buffer = generate_transcription_docx(meeting.name, meeting.transcriptions)
    save_formatted_transcription_and_update_meeting_status(
        meeting_id=meeting.id, file_like_object=docx_buffer, filename="v0.docx"
    )

    return docx_buffer


def save_formatted_transcription_and_update_meeting_status(
    meeting_id: int, file_like_object: BinaryIO, filename: Optional[str]
) -> None:
    name = filename if filename is not None else DEFAULT_TRANSCRIPTION_FILENAME

    content = BytesIO(file_like_object.read())
    file_like_object.seek(0)
    object_name = get_transcription_object_name(meeting_id=meeting_id, filename=name)
    put_file_to_s3(
        content=content, object_name=object_name, content_type=DOCX_MIME_TYPE
    )

    set_meeting_transcription_filename_and_update_status(
        meeting_id=meeting_id,
        filename=name,
    )


def create_evaluation_task_service(zip_bytes: bytes) -> None:
    try:
        celery_producer_app.send_task(MCRTranscriptionTasks.EVALUATE, args=[zip_bytes])
        logger.info("Evaluation task created")

    except Exception as e:
        logger.error("Error creating transcription task: {}", e)
        raise TaskCreationException(str(e))
