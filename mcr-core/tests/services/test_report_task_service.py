from io import BytesIO
from typing import Any

import pytest
from pytest_mock import MockerFixture

from mcr_meeting.app.exceptions.exceptions import MCRException
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.schemas.report_generation import (
    DetailedSynthesisGenerationResponse,
    ReportGenerationResponse,
    ReportHeader,
)
from mcr_meeting.app.services import report_task_service as rts
from tests.factories import MeetingFactory


def _decision_response() -> ReportGenerationResponse:
    return ReportGenerationResponse(
        header=ReportHeader(
            title="t", objective=None, participants=[], next_meeting=None
        ),
        topics_with_decision=[],
        next_steps=[],
    )


def _detailed_synthesis_response() -> DetailedSynthesisGenerationResponse:
    return DetailedSynthesisGenerationResponse(
        header=ReportHeader(
            title="t", objective=None, participants=[], next_meeting=None
        ),
        discussions_summary=[],
        detailed_discussions=[],
        to_do_list=[],
        to_monitor_list=[],
    )


class TestDeliverableObjectFilename:
    @pytest.mark.parametrize(
        "deliverable_type,expected",
        [
            (DeliverableType.DECISION_RECORD, "decision_record.docx"),
            (DeliverableType.DETAILED_SYNTHESIS, "detailed_synthesis.docx"),
            (DeliverableType.TRANSCRIPTION, "transcription.docx"),
        ],
    )
    def test_returns_lowercase_value_with_docx_suffix(
        self, deliverable_type: DeliverableType, expected: str
    ) -> None:
        assert rts.deliverable_object_filename(deliverable_type) == expected

    def test_unique_per_member(self) -> None:
        names = {rts.deliverable_object_filename(t) for t in DeliverableType}
        assert len(names) == len(list(DeliverableType))
        for name in names:
            assert name and name.endswith(".docx")


class TestPersistReportDocx:
    def test_decision_record_writes_typed_filename(
        self,
        mocker: MockerFixture,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING, name_platform=MeetingPlatforms.COMU
        )
        save_mock = mocker.patch(
            "mcr_meeting.app.services.report_task_service.save_formatted_report"
        )
        gen_mock = mocker.patch(
            "mcr_meeting.app.services.report_task_service.generate_docx_decisions_reports_from_template",
            return_value=BytesIO(b"docx"),
        )

        rts.persist_report_docx(
            meeting_id=meeting.id,
            report_response=_decision_response(),
        )

        gen_mock.assert_called_once()
        save_mock.assert_called_once()
        assert save_mock.call_args.kwargs["meeting_id"] == meeting.id
        assert save_mock.call_args.kwargs["filename"] == "decision_record.docx"

    def test_detailed_synthesis_writes_typed_filename(
        self,
        mocker: MockerFixture,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING, name_platform=MeetingPlatforms.COMU
        )
        save_mock = mocker.patch(
            "mcr_meeting.app.services.report_task_service.save_formatted_report"
        )
        mocker.patch(
            "mcr_meeting.app.services.report_task_service.generate_detailed_synthesis_docx",
            return_value=BytesIO(b"docx"),
        )

        rts.persist_report_docx(
            meeting_id=meeting.id,
            report_response=_detailed_synthesis_response(),
        )

        save_mock.assert_called_once()
        assert save_mock.call_args.kwargs["filename"] == "detailed_synthesis.docx"

    def test_raises_for_unknown_response_type(
        self,
        mocker: MockerFixture,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_PENDING, name_platform=MeetingPlatforms.COMU
        )
        mocker.patch(
            "mcr_meeting.app.services.report_task_service.save_formatted_report"
        )

        class _Bogus:
            pass

        with pytest.raises(MCRException):
            rts.persist_report_docx(
                meeting_id=meeting.id,
                report_response=_Bogus(),  # type: ignore[arg-type]
            )


class TestGetTypedDeliverableFromS3:
    def test_returns_bytes_on_hit(
        self,
        mocker: MockerFixture,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE, name_platform=MeetingPlatforms.COMU
        )
        buffer = BytesIO(b"typed bytes")
        mocker.patch(
            "mcr_meeting.app.services.report_task_service.get_file_from_s3_or_none",
            return_value=buffer,
        )

        result = rts.get_typed_deliverable_from_s3(
            meeting=meeting, deliverable_type=DeliverableType.DECISION_RECORD
        )

        assert result is buffer

    def test_returns_none_on_miss(
        self,
        mocker: MockerFixture,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE, name_platform=MeetingPlatforms.COMU
        )
        mocker.patch(
            "mcr_meeting.app.services.report_task_service.get_file_from_s3_or_none",
            return_value=None,
        )

        result = rts.get_typed_deliverable_from_s3(
            meeting=meeting, deliverable_type=DeliverableType.DECISION_RECORD
        )

        assert result is None

    def test_uses_typed_object_name(
        self,
        mocker: MockerFixture,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.REPORT_DONE, name_platform=MeetingPlatforms.COMU
        )
        captured: dict[str, Any] = {}

        def _capture(object_name: str) -> BytesIO:
            captured["object_name"] = object_name
            return BytesIO(b"x")

        mocker.patch(
            "mcr_meeting.app.services.report_task_service.get_file_from_s3_or_none",
            side_effect=_capture,
        )

        rts.get_typed_deliverable_from_s3(
            meeting=meeting, deliverable_type=DeliverableType.DETAILED_SYNTHESIS
        )

        assert captured["object_name"].endswith(
            f"/{meeting.id}/detailed_synthesis.docx"
        )
