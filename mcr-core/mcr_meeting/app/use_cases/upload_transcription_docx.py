from io import BytesIO
from typing import BinaryIO

from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id, update_meeting
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.domain.meeting_transitions import (
    update_transcription as apply_update_transcription,
)
from mcr_meeting.app.infrastructure.s3 import upload_transcription_to_s3

DEFAULT_TRANSCRIPTION_FILENAME = "transcription.docx"


def upload_transcription_docx(
    meeting_id: int,
    file_obj: BinaryIO,
    filename: str | None,
    user_keycloak_uuid: UUID4,
) -> None:
    """Store a user-edited transcription DOCX as the meeting's current version."""
    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)
    apply_update_transcription(meeting)

    name = filename if filename is not None else DEFAULT_TRANSCRIPTION_FILENAME
    content = BytesIO(file_obj.read())
    file_obj.seek(0)
    upload_transcription_to_s3(meeting_id=meeting.id, filename=name, content=content)

    meeting.transcription_filename = name
    with UnitOfWork():
        update_meeting(meeting)
