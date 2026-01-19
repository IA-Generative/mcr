from fastapi import APIRouter, Depends, Header, status
from pydantic import UUID4

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import router_db_session_context_manager
from mcr_meeting.app.orchestrators.meeting_multipart_orchestrator import (
    abort_multipart_upload_orchestrator,
    complete_multipart_upload_orchestrator,
    init_multipart_upload_orchestrator,
    sign_multipart_part_orchestrator,
)
from mcr_meeting.app.schemas.S3_types import (
    MultipartAbortRequest,
    MultipartCompleteRequest,
    MultipartInitRequest,
    MultipartInitResponse,
    MultipartSignPartRequest,
    MultipartSignPartResponse,
)

api_settings = ApiSettings()
router = APIRouter(
    prefix=api_settings.MEETING_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Meetings", "Audio"],
)


@router.post("/{meeting_id}/multipart/init")
def init_multipart_upload(
    meeting_id: int,
    init_request: MultipartInitRequest,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> MultipartInitResponse:
    return init_multipart_upload_orchestrator(
        meeting_id=meeting_id,
        user_keycloak_uuid=x_user_keycloak_uuid,
        init_request=init_request,
    )


@router.post("/{meeting_id}/multipart/sign")
def sign_multipart_part(
    meeting_id: int,
    sign_request: MultipartSignPartRequest,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> MultipartSignPartResponse:
    return sign_multipart_part_orchestrator(
        meeting_id=meeting_id,
        user_keycloak_uuid=x_user_keycloak_uuid,
        sign_request=sign_request,
    )


@router.post(
    "/{meeting_id}/multipart/complete",
    status_code=status.HTTP_204_NO_CONTENT,
)
def complete_multipart_upload(
    meeting_id: int,
    complete_request: MultipartCompleteRequest,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> None:
    complete_multipart_upload_orchestrator(
        meeting_id=meeting_id,
        user_keycloak_uuid=x_user_keycloak_uuid,
        complete_request=complete_request,
    )


@router.post(
    "/{meeting_id}/multipart/abort",
    status_code=status.HTTP_204_NO_CONTENT,
)
def abort_multipart_upload(
    meeting_id: int,
    abort_request: MultipartAbortRequest,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> None:
    abort_multipart_upload_orchestrator(
        meeting_id=meeting_id,
        user_keycloak_uuid=x_user_keycloak_uuid,
        abort_request=abort_request,
    )
