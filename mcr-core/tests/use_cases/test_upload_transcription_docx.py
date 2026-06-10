from io import BytesIO
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.use_cases.upload_transcription_docx import (
    upload_transcription_docx,
)
from tests.factories import MeetingFactory
from tests.mocks.in_memory_s3 import InMemoryS3


def test_upload_stores_docx_and_keeps_status_done(
    in_memory_s3: InMemoryS3, db_session: Session
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    upload_transcription_docx(
        meeting_id=meeting.id,
        file_obj=BytesIO(b"edited docx"),
        filename="edited.docx",
        user_keycloak_uuid=meeting.owner.keycloak_uuid,
    )

    db_session.refresh(meeting)
    assert meeting.transcription_filename == "edited.docx"
    assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE
    assert len(in_memory_s3.objects) == 1


def test_upload_rejects_non_owner(in_memory_s3: InMemoryS3) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(ForbiddenAccessException):
        upload_transcription_docx(
            meeting_id=meeting.id,
            file_obj=BytesIO(b"edited docx"),
            filename="edited.docx",
            user_keycloak_uuid=uuid4(),
        )


def test_upload_rejects_illegal_transition(in_memory_s3: InMemoryS3) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(ValueError):
        upload_transcription_docx(
            meeting_id=meeting.id,
            file_obj=BytesIO(b"edited docx"),
            filename="edited.docx",
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
        )
