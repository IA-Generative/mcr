from pydantic import UUID4

from mcr_meeting.app.exceptions.exceptions import (
    MeetingMultipartException,
)
from mcr_meeting.app.schemas.S3_types import (
    MultipartAbortRequest,
    MultipartBaseRequest,
    MultipartCompleteRequest,
    MultipartInitRequest,
    MultipartInitResponse,
    MultipartSignPartRequest,
    MultipartSignPartResponse,
)
from mcr_meeting.app.services.meeting_service import get_meeting_service
from mcr_meeting.app.services.s3_service import (
    abort_multipart_upload,
    complete_multipart_upload,
    create_multipart_upload,
    get_audio_object_prefix,
    get_presigned_url_for_upload_part,
)


def init_multipart_upload_service(
    meeting_id: int,
    current_user_keycloak_uuid: UUID4,
    init_request: MultipartInitRequest,
) -> MultipartInitResponse:
    _ = get_meeting_service(meeting_id, current_user_keycloak_uuid)

    result = create_multipart_upload(meeting_id=meeting_id, init_request=init_request)

    return MultipartInitResponse(
        upload_id=result["upload_id"], object_key=result["key"]
    )


def sign_multipart_part_service(
    meeting_id: int,
    current_user_keycloak_uuid: UUID4,
    sign_request: MultipartSignPartRequest,
) -> MultipartSignPartResponse:
    _ = get_meeting_service(meeting_id, current_user_keycloak_uuid)

    check_audio_file_prefix(meeting_id, sign_request)

    url = get_presigned_url_for_upload_part(
        object_key=sign_request.object_key,
        upload_id=sign_request.upload_id,
        part_number=sign_request.part_number,
    )
    return MultipartSignPartResponse(url=url)


def complete_multipart_upload_service(
    meeting_id: int,
    current_user_keycloak_uuid: UUID4,
    complete_request: MultipartCompleteRequest,
) -> None:
    _ = get_meeting_service(meeting_id, current_user_keycloak_uuid)

    check_audio_file_prefix(meeting_id, complete_request)

    complete_multipart_upload(complete_request)


def abort_multipart_upload_service(
    meeting_id: int,
    current_user_keycloak_uuid: UUID4,
    abort_request: MultipartAbortRequest,
) -> None:
    _ = get_meeting_service(meeting_id, current_user_keycloak_uuid)

    check_audio_file_prefix(meeting_id, abort_request)

    abort_multipart_upload(
        object_key=abort_request.object_key, upload_id=abort_request.upload_id
    )


def check_audio_file_prefix(meeting_id: int, request: MultipartBaseRequest) -> None:
    expected_prefix = get_audio_object_prefix(str(meeting_id))
    if not request.object_key.startswith(expected_prefix):
        raise MeetingMultipartException("Invalid object key for this meeting.")
