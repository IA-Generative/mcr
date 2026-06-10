from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import UUID4

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import (
    router_db_session_context_manager,
)
from mcr_meeting.app.exceptions.exceptions import InvalidFileError
from mcr_meeting.app.schemas.transcription_schema import (
    SpeakerTranscription,
)
from mcr_meeting.app.use_cases.complete_transcription import complete_transcription
from mcr_meeting.app.use_cases.ensure_offline_token import ensure_offline_token
from mcr_meeting.app.use_cases.fail_transcription import fail_transcription
from mcr_meeting.app.use_cases.get_or_create_transcription_docx import (
    get_or_create_transcription_docx,
)
from mcr_meeting.app.use_cases.init_transcription import init_transcription
from mcr_meeting.app.use_cases.start_transcription import start_transcription
from mcr_meeting.app.use_cases.upload_transcription_docx import (
    upload_transcription_docx,
)
from mcr_meeting.app.utils.file_validation import DOCX_MIME_TYPE, validate_docx_upload
from mcr_meeting.app.utils.filename_header import create_safe_filename_header

api_settings = ApiSettings()

router = APIRouter(
    prefix=api_settings.MEETING_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Meetings", "Transcription"],
)


@router.post("/{meeting_id}/transcription")
async def retrieve_or_create_formatted_meeting_transcription(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> StreamingResponse:
    """
    Get the transcription DOCX file of a given meeting

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        DOCX file of the transcription meeting

    """

    result = get_or_create_transcription_docx(
        meeting_id=meeting_id, user_keycloak_uuid=x_user_keycloak_uuid
    )

    headers = create_safe_filename_header(result.filename)

    return StreamingResponse(
        result.buffer,
        media_type=DOCX_MIME_TYPE,
        headers=headers,
    )


@router.put("/{meeting_id}/transcription", status_code=status.HTTP_204_NO_CONTENT)
async def upload_meeting_transcription(
    file: UploadFile,
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> None:
    """
    Adds the modified transcription with a new version to a given meeting

    Args:
        meeting_id (int): The ID of the meeting.
        file: Transcription DOCX file

    Returns:
        204 if the transcription has been added

    """
    try:
        await validate_docx_upload(file)
    except InvalidFileError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file type. Please upload a DOCX file.",
        )

    upload_transcription_docx(
        meeting_id=meeting_id,
        file_obj=file.file,
        filename=file.filename,
        user_keycloak_uuid=x_user_keycloak_uuid,
    )


@router.post("/{meeting_id}/transcription/init", status_code=status.HTTP_204_NO_CONTENT)
async def init_transcription_task(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 | None = Header(default=None),
    x_user_access_token: str | None = Header(default=None),
) -> None:
    init_transcription(meeting_id=meeting_id)
    if x_user_keycloak_uuid is not None:
        ensure_offline_token(str(x_user_keycloak_uuid), x_user_access_token)


@router.post(
    "/{meeting_id}/transcription/start", status_code=status.HTTP_204_NO_CONTENT
)
async def start_transcription_task(meeting_id: int) -> None:
    start_transcription(meeting_id=meeting_id)


@router.post("/{meeting_id}/transcription/fail", status_code=status.HTTP_204_NO_CONTENT)
async def fail_transcription_task(meeting_id: int) -> None:
    fail_transcription(meeting_id=meeting_id)


@router.post(
    "/{meeting_id}/transcription/success", status_code=status.HTTP_204_NO_CONTENT
)
async def success_transcription_task(
    meeting_id: int, payload: list[SpeakerTranscription]
) -> None:
    complete_transcription(meeting_id=meeting_id, transcriptions=payload)
