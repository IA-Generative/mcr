from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.infrastructure.s3 import (
    abort_multipart_upload as abort_multipart_upload_in_s3,
)
from mcr_meeting.app.schemas.S3_types import MultipartAbortRequest


def abort_multipart_upload(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    abort_request: MultipartAbortRequest,
) -> None:
    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)
    abort_multipart_upload_in_s3(meeting_id, abort_request)
