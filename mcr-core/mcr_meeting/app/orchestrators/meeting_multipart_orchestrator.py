from pydantic import UUID4

from mcr_meeting.app.schemas.S3_types import (
    MultipartAbortRequest,
    MultipartCompleteRequest,
    MultipartInitRequest,
    MultipartInitResponse,
    MultipartSignPartRequest,
    MultipartSignPartResponse,
)
from mcr_meeting.app.services.meeting_multipart_service import (
    abort_multipart_upload_service,
    complete_multipart_upload_service,
    init_multipart_upload_service,
    sign_multipart_part_service,
)


def init_multipart_upload_orchestrator(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    init_request: MultipartInitRequest,
) -> MultipartInitResponse:
    return init_multipart_upload_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
        init_request=init_request,
    )


def sign_multipart_part_orchestrator(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    sign_request: MultipartSignPartRequest,
) -> MultipartSignPartResponse:
    return sign_multipart_part_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
        sign_request=sign_request,
    )


def complete_multipart_upload_orchestrator(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    complete_request: MultipartCompleteRequest,
) -> None:
    return complete_multipart_upload_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
        complete_request=complete_request,
    )


def abort_multipart_upload_orchestrator(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    abort_request: MultipartAbortRequest,
) -> None:
    return abort_multipart_upload_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
        abort_request=abort_request,
    )
