from typing import Optional

from fastapi import UploadFile
from pydantic import UUID4

from mcr_meeting.app.orchestrators.meeting_transitions_orchestrator import (
    complete_transcription,
)
from mcr_meeting.app.schemas.transcription_queue_schema import (
    TranscriptionQueueStatusResponse,
)
from mcr_meeting.app.schemas.transcription_schema import TranscriptionDocxResult
from mcr_meeting.app.services.meeting_service import (
    get_meeting_service,
    get_meeting_with_transcriptions_service,
)
from mcr_meeting.app.services.transcription_task_service import (
    retrieve_or_create_formatted_docx_transcription,
    save_formatted_transcription_and_update_meeting_status,
)
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)


async def get_or_create_transcription_docx(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> TranscriptionDocxResult:
    meeting = get_meeting_with_transcriptions_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
    )

    docx_buffer = await retrieve_or_create_formatted_docx_transcription(meeting)

    filename = f"Transcription_{meeting.name}.docx"

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

    complete_transcription(meeting_id=meeting_id)


def get_transcription_waiting_time(
    meeting_id: int,
    user_keycloak_uuid: Optional[UUID4] = None,
) -> TranscriptionQueueStatusResponse:
    get_meeting_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
    )

    waiting_time_minutes = (
        TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes(
            meeting_id
        )
    )

    return TranscriptionQueueStatusResponse(
        estimation_duration_minutes=waiting_time_minutes
    )
