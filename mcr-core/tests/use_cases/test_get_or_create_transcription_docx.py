from io import BytesIO
from uuid import uuid4

import pytest

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.infrastructure.s3 import upload_transcription_to_s3
from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.use_cases.get_or_create_transcription_docx import (
    INITIAL_TRANSCRIPTION_FILENAME,
    get_or_create_transcription_docx,
)
from tests.factories import MeetingFactory, UserFactory
from tests.factories.transcription_factory import TranscriptionFactory
from tests.mocks.in_memory_s3 import InMemoryS3


def test_renders_and_stores_docx_when_no_filename(
    in_memory_s3: InMemoryS3,
) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
        transcription_filename=None,
    )
    TranscriptionFactory.create_batch(2, meeting=meeting)

    result = get_or_create_transcription_docx(
        meeting_id=meeting.id, user_keycloak_uuid=meeting.owner.keycloak_uuid
    )

    assert result.filename.endswith(".docx")
    assert len(in_memory_s3.objects) == 1
    assert meeting.transcription_filename == INITIAL_TRANSCRIPTION_FILENAME


def test_returns_existing_docx_from_s3(in_memory_s3: InMemoryS3) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
        transcription_filename=INITIAL_TRANSCRIPTION_FILENAME,
    )
    upload_transcription_to_s3(
        meeting_id=meeting.id,
        filename=INITIAL_TRANSCRIPTION_FILENAME,
        content=BytesIO(b"stored docx"),
    )

    result = get_or_create_transcription_docx(
        meeting_id=meeting.id, user_keycloak_uuid=meeting.owner.keycloak_uuid
    )

    assert result.buffer.read() == b"stored docx"
    # No new object created when one already exists.
    assert len(in_memory_s3.objects) == 1


def test_rejects_non_owner(in_memory_s3: InMemoryS3) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(ForbiddenAccessException):
        get_or_create_transcription_docx(
            meeting_id=meeting.id, user_keycloak_uuid=uuid4()
        )


def test_rejects_other_existing_user(in_memory_s3: InMemoryS3) -> None:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
    )
    other_user = UserFactory.create()

    with pytest.raises(ForbiddenAccessException):
        get_or_create_transcription_docx(
            meeting_id=meeting.id, user_keycloak_uuid=other_user.keycloak_uuid
        )
