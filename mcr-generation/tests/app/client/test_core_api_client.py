"""HTTP-level unit tests for CoreApiClient."""

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from mcr_generation.app.client.core_api_client import CoreApiClient
from mcr_generation.app.exceptions.exceptions import ReportCallbackError
from mcr_generation.app.schemas.base import (
    DecisionRecord,
    Header,
    Participant,
    Topic,
)


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    response = MagicMock()
    response.status_code = status_code
    return httpx.HTTPStatusError(
        f"{status_code}",
        request=MagicMock(),
        response=response,
    )


@pytest.fixture
def mock_httpx_client(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    """Replaces httpx.Client at the http_client module level."""
    instance = MagicMock()
    instance.__enter__ = MagicMock(return_value=instance)
    instance.__exit__ = MagicMock(return_value=False)
    cls = MagicMock(return_value=instance)
    monkeypatch.setattr("mcr_generation.app.client.http_client.httpx.Client", cls)
    return instance


@pytest.fixture
def core_client() -> CoreApiClient:
    return CoreApiClient()


@pytest.fixture
def decision_record() -> DecisionRecord:
    return DecisionRecord(
        header=Header(
            title="t",
            objective="o",
            participants=[
                Participant(
                    speaker_id="LOCUTEUR_00",
                    name="A",
                    role="r",
                    confidence=0.9,
                    association_justification="j",
                )
            ],
            next_meeting=None,
        ),
        topics_with_decision=[
            Topic(
                title="t",
                introduction_text="i",
                details=["d"],
                main_decision="m",
            )
        ],
        next_steps=["n"],
    )


def _expected_payload(report: DecisionRecord) -> dict[str, Any]:
    return {
        "next_steps": report.next_steps,
        "topics_with_decision": [t.model_dump() for t in report.topics_with_decision],
        "header": {
            "title": report.header.title,
            "objective": report.header.objective,
            "next_meeting": report.header.next_meeting,
            "participants": [
                p.model_dump(exclude={"association_justification"})
                for p in report.header.participants
            ],
        },
    }


class TestMarkReportSuccess:
    def test_posts_report_payload(
        self,
        core_client: CoreApiClient,
        mock_httpx_client: MagicMock,
        decision_record: DecisionRecord,
    ) -> None:
        core_client.mark_report_success(meeting_id=42, report=decision_record)

        mock_httpx_client.post.assert_called_once()
        call = mock_httpx_client.post.call_args
        assert call.args[0] == "/meetings/42/report/success"
        assert call.kwargs["json"] == _expected_payload(decision_record)

    def test_wraps_http_error_as_report_callback_error(
        self,
        core_client: CoreApiClient,
        mock_httpx_client: MagicMock,
        decision_record: DecisionRecord,
    ) -> None:
        mock_httpx_client.post.return_value.raise_for_status.side_effect = _http_error(
            500
        )

        with pytest.raises(ReportCallbackError):
            core_client.mark_report_success(meeting_id=42, report=decision_record)


class TestMarkReportFailure:
    def test_posts_to_failure_endpoint(
        self,
        core_client: CoreApiClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        core_client.mark_report_failure(meeting_id=42)

        mock_httpx_client.post.assert_called_once()
        assert mock_httpx_client.post.call_args.args[0] == "/meetings/42/report/failure"

    def test_wraps_http_error_as_report_callback_error(
        self,
        core_client: CoreApiClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        mock_httpx_client.post.return_value.raise_for_status.side_effect = _http_error(
            500
        )

        with pytest.raises(ReportCallbackError):
            core_client.mark_report_failure(meeting_id=42)
