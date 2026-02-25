"""
Unit tests for report_generation_task_service signal handlers.
"""

import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pytest import fixture

from mcr_generation.app.schemas.base import (
    DecisionRecord,
    Header,
    Participant,
    Topic,
)

# ---------------------------------------------------------------------------
# Patch modules with side effects at import time BEFORE the service is imported.
# ---------------------------------------------------------------------------
_mock_langfuse = MagicMock()
_mock_langfuse.observe = lambda *args, **kwargs: (lambda fn: fn)
sys.modules["langfuse"] = _mock_langfuse

_mock_celery_worker = MagicMock()
_mock_celery_worker.celery_app.task = lambda *args, **kwargs: (lambda fn: fn)
sys.modules["mcr_generation.app.utils.celery_worker"] = _mock_celery_worker

for _mod in [
    "mcr_generation.app.utils.s3_client",
    "mcr_generation.app.services.utils.s3_service",
    "mcr_generation.app.services.utils.input_chunker",
    "mcr_generation.app.services.sections",
    "mcr_generation.app.services.sections.intent",
    "mcr_generation.app.services.sections.intent.refine_intent",
    "mcr_generation.app.services.sections.next_meeting",
    "mcr_generation.app.services.sections.next_meeting.refine_next_meeting",
    "mcr_generation.app.services.sections.next_meeting.format_section_for_report",
    "mcr_generation.app.services.sections.participants",
    "mcr_generation.app.services.sections.participants.refine_participants",
    "mcr_generation.app.services.sections.topics",
    "mcr_generation.app.services.sections.topics.map_reduce_topics",
    "mcr_generation.app.services.report_generator",
    "mcr_generation.app.services.report_generator.base_report_generator",
    "mcr_generation.app.services.report_generator.decision_record_generator",
]:
    sys.modules[_mod] = MagicMock()
# ---------------------------------------------------------------------------
# This import must come AFTER the sys.modules patches above.
# If imported earlier, Python would load the real modules (langfuse, celery, etc.)
# before the mocks are in place, breaking the tests.
# E402 is suppressed intentionally here.

from mcr_generation.app.services.report_generation_task_service import (  # noqa: E402
    generate_report_from_docx,
    generate_report_from_docx_success,
    set_meeting_failed_status_on_error,
)


@fixture
def decision_record() -> DecisionRecord:
    return DecisionRecord(
        header=Header(
            title="Réunion Budget Q1",
            objective="Valider le budget du premier trimestre",
            participants=[
                Participant(
                    speaker_id="LOCUTEUR_00",
                    name="Alice Martin",
                    role="Directrice financière",
                    confidence=0.9,
                    association_justification="Mentionné plusieurs fois par son nom",
                )
            ],
            next_meeting="15/03/2026 à 10h00",
        ),
        topics_with_decision=[
            Topic(
                title="Budget marketing",
                introduction_text="Discussion autour du budget alloué au marketing.",
                details=["Budget actuel : 50k€", "Objectif : -10%"],
                main_decision="Alice a décidé de réduire le budget de 10%.",
            )
        ],
        next_steps=["Envoyer le compte-rendu à l'équipe"],
    )


MODULE = "mcr_generation.app.services.report_generation_task_service"


class TestGenerateReportFromDocx:
    def test_returns_decision_record_built_from_service_outputs(
        self, decision_record: DecisionRecord
    ) -> None:
        """Happy path: get_generator is mocked and its generate() return value is
        forwarded as-is by the task."""
        mock_chunks = ["chunk1", "chunk2"]
        mock_docx_bytes = b"docx content"

        mock_generator = MagicMock()
        mock_generator.generate.return_value = decision_record

        with (
            patch(
                f"{MODULE}.get_file_from_s3", return_value=mock_docx_bytes
            ) as mock_s3,
            patch(
                f"{MODULE}.chunk_docx_to_document_list", return_value=mock_chunks
            ) as mock_chunker,
            patch(
                f"{MODULE}.get_generator", return_value=mock_generator
            ) as mock_get_generator,
        ):
            result = generate_report_from_docx(1, "transcription.docx")

        assert result == decision_record

        mock_s3.assert_called_once_with("transcription.docx")
        mock_chunker.assert_called_once_with(mock_docx_bytes)
        mock_get_generator.assert_called_once()
        mock_generator.generate.assert_called_once_with(mock_chunks)

    def test_propagates_s3_error(self) -> None:
        """An exception raised by get_file_from_s3 must propagate."""
        with patch(
            f"{MODULE}.get_file_from_s3", side_effect=RuntimeError("S3 unavailable")
        ):
            with pytest.raises(RuntimeError, match="S3 unavailable"):
                generate_report_from_docx(1, "transcription.docx")


class TestGenerateReportFromDocxSuccess:
    def _make_mock_http_client(self, mock_response: MagicMock) -> MagicMock:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        return mock_client

    def test_logs_error_and_returns_when_args_empty(
        self, decision_record: DecisionRecord
    ) -> None:
        """When sender has no request args, the function returns early without calling httpx."""
        sender = MagicMock()
        sender.request.args = []

        with patch(f"{MODULE}.httpx.Client") as mock_client_cls:
            generate_report_from_docx_success(sender=sender, result=decision_record)

        mock_client_cls.assert_not_called()

    def test_posts_report_to_correct_endpoint(
        self, decision_record: DecisionRecord
    ) -> None:
        """When args contain a meeting_id, the report payload is POSTed to the right URL."""
        sender = MagicMock()
        sender.request.args = [42]
        result = decision_record

        mock_response = MagicMock()
        mock_client = self._make_mock_http_client(mock_response)
        mock_api_settings = MagicMock()
        mock_api_settings.MCR_CORE_API_URL = "http://mcr-core/api"

        expected_payload = {
            "next_steps": result.next_steps,
            "topics_with_decision": [
                topic.model_dump() for topic in result.topics_with_decision
            ],
            "header": {
                "title": result.header.title,
                "objective": result.header.objective,
                "next_meeting": result.header.next_meeting,
                "participants": [
                    p.model_dump(exclude={"association_justification"})
                    for p in result.header.participants
                ],
            },
        }

        with patch(f"{MODULE}.api_settings", mock_api_settings):
            with patch(f"{MODULE}.httpx.Client", return_value=mock_client):
                generate_report_from_docx_success(sender=sender, result=result)

        mock_client.post.assert_called_once_with(
            "/meetings/42/report/success",
            json=expected_payload,
        )
        mock_response.raise_for_status.assert_called_once()

    def test_raises_on_http_error(self, decision_record: DecisionRecord) -> None:
        """An HTTPStatusError from raise_for_status() propagates to the caller."""
        sender = MagicMock()
        sender.request.args = [1]

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=MagicMock(),
        )
        mock_client = self._make_mock_http_client(mock_response)
        mock_api_settings = MagicMock()
        mock_api_settings.MCR_CORE_API_URL = "http://mcr-core/api"

        with patch(f"{MODULE}.api_settings", mock_api_settings):
            with patch(f"{MODULE}.httpx.Client", return_value=mock_client):
                with pytest.raises(httpx.HTTPStatusError):
                    generate_report_from_docx_success(
                        sender=sender, result=decision_record
                    )


class TestSetMeetingFailedStatusOnError:
    def test_is_noop_with_no_args(self) -> None:
        """Function is a no-op and should never raise."""
        set_meeting_failed_status_on_error()

    def test_is_noop_with_sender_and_kwargs(self) -> None:
        """Function is a no-op regardless of the arguments passed."""
        set_meeting_failed_status_on_error(
            sender=MagicMock(), exception=Exception("fail"), traceback=None
        )
