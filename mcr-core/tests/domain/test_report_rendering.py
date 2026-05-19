from io import BytesIO

import pytest
from pytest_mock import MockerFixture

from mcr_meeting.app.domain.report_rendering import render_report
from mcr_meeting.app.exceptions.exceptions import MCRException
from mcr_meeting.app.schemas.report_generation import (
    CustomReportResponse,
    DetailedSynthesisGenerationResponse,
    ReportGenerationResponse,
    ReportHeader,
)


def _empty_header() -> ReportHeader:
    return ReportHeader(title=None, objective=None, participants=[], next_meeting=None)


def _decision_response() -> ReportGenerationResponse:
    return ReportGenerationResponse(
        header=_empty_header(), topics_with_decision=[], next_steps=[]
    )


def _detailed_synthesis_response() -> DetailedSynthesisGenerationResponse:
    return DetailedSynthesisGenerationResponse(
        header=_empty_header(),
        discussions_summary=[],
        detailed_discussions=[],
        to_do_list=[],
        to_monitor_list=[],
    )


def test_routes_decision_record_to_template_generator(mocker: MockerFixture) -> None:
    gen = mocker.patch(
        "mcr_meeting.app.domain.report_rendering."
        "generate_docx_decisions_reports_from_template",
        return_value=BytesIO(b"docx"),
    )

    result = render_report(_decision_response(), meeting_name="My meeting")

    gen.assert_called_once()
    assert result.getvalue() == b"docx"


def test_routes_detailed_synthesis_to_synthesis_generator(
    mocker: MockerFixture,
) -> None:
    gen = mocker.patch(
        "mcr_meeting.app.domain.report_rendering.generate_detailed_synthesis_docx",
        return_value=BytesIO(b"docx"),
    )

    result = render_report(_detailed_synthesis_response(), meeting_name="My meeting")

    gen.assert_called_once()
    assert result.getvalue() == b"docx"


def test_routes_custom_report_to_custom_generator(mocker: MockerFixture) -> None:
    gen = mocker.patch(
        "mcr_meeting.app.domain.report_rendering.generate_custom_report_docx",
        return_value=BytesIO(b"docx"),
    )

    result = render_report(
        CustomReportResponse(markdown_content="# Test"), meeting_name="My meeting"
    )

    gen.assert_called_once()
    assert result.getvalue() == b"docx"


def test_raises_for_unknown_response_type() -> None:
    class _Bogus:
        pass

    with pytest.raises(MCRException):
        render_report(_Bogus(), meeting_name="My meeting")  # type: ignore[arg-type]
