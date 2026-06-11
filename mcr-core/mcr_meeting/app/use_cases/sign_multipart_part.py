from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.infrastructure.s3 import (
    sign_multipart_part as sign_multipart_part_in_s3,
)
from mcr_meeting.app.schemas.S3_types import (
    MultipartSignPartRequest,
    MultipartSignPartResponse,
)


def sign_multipart_part(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    sign_request: MultipartSignPartRequest,
) -> MultipartSignPartResponse:
    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)
    return sign_multipart_part_in_s3(meeting_id, sign_request)
