from io import BytesIO

from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import (
    get_meeting_with_transcriptions,
    update_meeting,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.domain.transcription_rendering import render_transcription_docx
from mcr_meeting.app.infrastructure.s3 import (
    download_transcription_docx,
    upload_transcription_to_s3,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.schemas.transcription_schema import TranscriptionDocxResult
from mcr_meeting.app.utils.deliverable_filename import build_deliverable_filename

INITIAL_TRANSCRIPTION_FILENAME = "v0.docx"


def get_or_create_transcription_docx(
    meeting_id: int, user_keycloak_uuid: UUID4
) -> TranscriptionDocxResult:
    meeting = get_meeting_with_transcriptions(meeting_id)
    authorize_meeting_access(meeting, user_keycloak_uuid)

    if meeting.transcription_filename is None:
        docx_buffer = _render_and_store(meeting)
    else:
        docx_buffer = download_transcription_docx(
            meeting_id=meeting.id, filename=meeting.transcription_filename
        )

    filename = build_deliverable_filename(
        deliverable_type=DeliverableType.TRANSCRIPTION,
        meeting_name=meeting.name or "",
    )

    return TranscriptionDocxResult(buffer=docx_buffer, filename=filename)


def _render_and_store(meeting: Meeting) -> BytesIO:
    docx_buffer = render_transcription_docx(meeting.name, meeting.transcriptions)
    upload_transcription_to_s3(
        meeting_id=meeting.id,
        filename=INITIAL_TRANSCRIPTION_FILENAME,
        content=docx_buffer,
    )
    meeting.transcription_filename = INITIAL_TRANSCRIPTION_FILENAME

    with UnitOfWork():
        update_meeting(meeting)

    return docx_buffer
