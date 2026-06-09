from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.infrastructure.s3 import (
    initiate_multipart_upload as initiate_multipart_upload_in_s3,
)
from mcr_meeting.app.schemas.S3_types import (
    MultipartInitRequest,
    MultipartInitResponse,
)


def init_multipart_upload(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    init_request: MultipartInitRequest,
) -> MultipartInitResponse:
    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)
    return initiate_multipart_upload_in_s3(meeting_id, init_request)
