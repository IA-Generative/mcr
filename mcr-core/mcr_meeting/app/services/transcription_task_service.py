from collections.abc import Sequence
from io import BytesIO
from typing import BinaryIO

from mcr_meeting.app.domain.transcription_rendering import (
    HasSpeakerTranscription,
    render_transcription_docx,
)
from mcr_meeting.app.exceptions.exceptions import (
    NotFoundException,
)
from mcr_meeting.app.infrastructure.s3 import get_transcription_object_name
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.services.meeting_service import (
    set_meeting_transcription_filename_and_update_status,
)
from mcr_meeting.app.services.s3_service import (
    get_file_from_s3,
    put_file_to_s3,
)
from mcr_meeting.app.utils.file_validation import DOCX_MIME_TYPE

DEFAULT_TRANSCRIPTION_FILENAME = "transcription.docx"


def retrieve_or_create_formatted_docx_transcription(meeting: Meeting) -> BytesIO:
    if meeting.transcription_filename is None:
        docx_buffer = create_formatted_docx_transcription(
            meeting, meeting.transcriptions
        )
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


def create_formatted_docx_transcription(
    meeting: Meeting,
    transcriptions: Sequence[HasSpeakerTranscription],
) -> BytesIO:
    docx_buffer = render_transcription_docx(meeting.name, transcriptions)
    save_formatted_transcription_and_update_meeting_status(
        meeting_id=meeting.id, file_like_object=docx_buffer, filename="v0.docx"
    )

    return docx_buffer


def save_formatted_transcription_and_update_meeting_status(
    meeting_id: int, file_like_object: BinaryIO, filename: str | None
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
