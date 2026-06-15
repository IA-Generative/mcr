from io import BytesIO
from typing import Any

import pytest

from mcr_meeting.app.exceptions.exceptions import (
    BadRequestException,
    NotFoundException,
)
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.use_cases.get_deliverable_file import get_deliverable_file
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory

_USE_CASE = "mcr_meeting.app.use_cases.get_deliverable_file"


class TestGetDeliverableFile:
    def test_streams_typed_file_when_present(
        self,
        mocker: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            report_filename="decision_record.docx",
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )
        typed_buffer = BytesIO(b"typed content")
        typed_mock = mocker.patch(
            f"{_USE_CASE}.get_typed_deliverable_from_s3",
            return_value=typed_buffer,
        )
        legacy_mock = mocker.patch(f"{_USE_CASE}.get_report_from_s3")

        result = get_deliverable_file(
            deliverable_id=deliverable.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
        )

        assert result.buffer is typed_buffer
        assert result.meeting_name == meeting.name
        typed_mock.assert_called_once()
        legacy_mock.assert_not_called()

    def test_falls_back_to_legacy_when_typed_missing(
        self,
        mocker: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            report_filename="report.docx",
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )
        legacy_buffer = BytesIO(b"legacy bytes")
        mocker.patch(
            f"{_USE_CASE}.get_typed_deliverable_from_s3",
            return_value=None,
        )
        legacy_mock = mocker.patch(
            f"{_USE_CASE}.get_report_from_s3",
            return_value=legacy_buffer,
        )

        result = get_deliverable_file(
            deliverable_id=deliverable.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
        )

        assert result.buffer is legacy_buffer
        legacy_mock.assert_called_once()

    def test_transcription_uses_transcription_file(
        self,
        mocker: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="v0.docx",
            report_filename="report.docx",
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )
        transcription_buffer = BytesIO(b"transcription bytes")
        typed_mock = mocker.patch(f"{_USE_CASE}.get_typed_deliverable_from_s3")
        report_mock = mocker.patch(f"{_USE_CASE}.get_report_from_s3")
        transcription_mock = mocker.patch(
            f"{_USE_CASE}.get_transcription_from_s3",
            return_value=transcription_buffer,
        )

        result = get_deliverable_file(
            deliverable_id=deliverable.id,
            user_keycloak_uuid=meeting.owner.keycloak_uuid,
        )

        assert result.buffer is transcription_buffer
        transcription_mock.assert_called_once_with(
            meeting.id, meeting.transcription_filename
        )
        typed_mock.assert_not_called()
        report_mock.assert_not_called()

    def test_transcription_without_filename_raises_not_found(
        self,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename=None,
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )

        with pytest.raises(NotFoundException):
            get_deliverable_file(
                deliverable_id=deliverable.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
            )

    def test_404_for_soft_deleted_deliverable(
        self,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            report_filename="report.docx",
        )
        deleted = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.DELETED,
        )

        with pytest.raises(NotFoundException):
            get_deliverable_file(
                deliverable_id=deleted.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
            )

    def test_rejects_pending_deliverable(
        self,
        mocker: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        pending = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )
        typed_mock = mocker.patch(f"{_USE_CASE}.get_typed_deliverable_from_s3")
        legacy_mock = mocker.patch(f"{_USE_CASE}.get_report_from_s3")

        with pytest.raises(BadRequestException):
            get_deliverable_file(
                deliverable_id=pending.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
            )
        typed_mock.assert_not_called()
        legacy_mock.assert_not_called()

    def test_rejects_failed_deliverable(
        self,
        mocker: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_FAILED,
            name_platform=MeetingPlatforms.COMU,
            report_filename="decision_record.docx",
        )
        failed = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.FAILED,
        )
        typed_mock = mocker.patch(
            f"{_USE_CASE}.get_typed_deliverable_from_s3",
            return_value=BytesIO(b"stale typed content"),
        )
        legacy_mock = mocker.patch(f"{_USE_CASE}.get_report_from_s3")

        with pytest.raises(BadRequestException):
            get_deliverable_file(
                deliverable_id=failed.id,
                user_keycloak_uuid=meeting.owner.keycloak_uuid,
            )
        typed_mock.assert_not_called()
        legacy_mock.assert_not_called()
