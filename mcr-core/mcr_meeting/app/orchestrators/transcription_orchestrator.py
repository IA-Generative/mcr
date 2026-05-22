from fastapi import UploadFile
from pydantic import UUID4

from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.orchestrators.meeting_transitions_orchestrator import (
    complete_transcription,
    update_transcription,
)
from mcr_meeting.app.schemas.transcription_schema import (
    SpeakerTranscription,
    TranscriptionDocxResult,
)
from mcr_meeting.app.services.meeting_service import (
    get_meeting_service,
    get_meeting_with_transcriptions_service,
)
from mcr_meeting.app.services.transcription_task_service import (
    create_formatted_docx_transcription,
    retrieve_or_create_formatted_docx_transcription,
    save_formatted_transcription_and_update_meeting_status,
)
from mcr_meeting.app.utils.deliverable_filename import build_deliverable_filename


def finalize_transcription(
    meeting_id: int,
    transcriptions: list[SpeakerTranscription],
) -> None:
    meeting = get_meeting_service(meeting_id=meeting_id)
    create_formatted_docx_transcription(meeting, transcriptions=transcriptions)
    complete_transcription(meeting_id=meeting_id)


async def get_or_create_transcription_docx(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> TranscriptionDocxResult:
    meeting = get_meeting_with_transcriptions_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
    )

    docx_buffer = retrieve_or_create_formatted_docx_transcription(meeting)

    filename = build_deliverable_filename(
        deliverable_type=DeliverableType.TRANSCRIPTION,
        meeting_name=meeting.name or "",
    )

    return TranscriptionDocxResult(
        buffer=docx_buffer,
        filename=filename,
    )


def upload_transcription_docx(
    meeting_id: int,
    file: UploadFile,
    user_keycloak_uuid: UUID4,
) -> None:
    get_meeting_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
    )

    save_formatted_transcription_and_update_meeting_status(
        meeting_id=meeting_id,
        file_like_object=file.file,
        filename=file.filename,
    )

    update_transcription(meeting_id=meeting_id, user_keycloak_uuid=user_keycloak_uuid)
