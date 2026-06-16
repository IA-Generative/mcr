from io import BytesIO

from mcr_meeting.app.exceptions.exceptions import (
    NotFoundException,
)
from mcr_meeting.app.infrastructure.s3 import get_transcription_object_name
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.services.s3_service import get_file_from_s3


def get_formatted_transcription_from_s3(meeting: Meeting) -> BytesIO:
    if meeting.transcription_filename is None:
        raise NotFoundException(
            "Couldn't get transcription as meeting.transcription_filename is empty"
        )
    object_name = get_transcription_object_name(
        meeting_id=meeting.id, filename=meeting.transcription_filename
    )
    return get_file_from_s3(object_name)
