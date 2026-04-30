"""
Unit tests for report_generation_task_service signal handlers.
"""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pytest import fixture

from mcr_generation.app.schemas.base import (
    DecisionRecord,
    Header,
    Participant,
    Topic,
)

# ---------------------------------------------------------------------------
# Mocks specific to this file (celery + report_generator package wholesale,
# since they are not the subject under test and initialise side effects).
# Common mocks (langfuse, openai, section modules, …) live in tests/conftest.py.
# ---------------------------------------------------------------------------
_mock_celery_worker = MagicMock()
_mock_celery_worker.celery_app.task = lambda *args, **kwargs: (lambda fn: fn)
sys.modules["mcr_generation.app.utils.celery_worker"] = _mock_celery_worker
sys.modules["mcr_generation.app.services.utils.input_chunker"] = MagicMock()
sys.modules["mcr_generation.app.services.report_generator"] = MagicMock()

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


class TestGenerateReportFromDocx:
    def test_returns_decision_record_built_from_service_outputs(
        self,
        decision_record: DecisionRecord,
        mock_get_file_from_s3: MagicMock,
        mock_chunk_docx_to_document_list: MagicMock,
        mock_get_generator: MagicMock,
    ) -> None:
        """Happy path: get_generator is mocked and its generate() return value is
        forwarded as-is by the task."""
        chunk1 = SimpleNamespace(id=0, text="chunk1")
        chunk2 = SimpleNamespace(id=1, text="chunk2")
        mock_get_file_from_s3.return_value = b"docx content"
        mock_chunk_docx_to_document_list.return_value = [chunk1, chunk2]
        mock_get_generator.return_value.generate.return_value = decision_record

        generate_report_from_docx(1, "transcription.docx")

        mock_get_file_from_s3.assert_called_once_with("transcription.docx")
        mock_chunk_docx_to_document_list.assert_called_once_with(b"docx content")
        mock_get_generator.assert_called_once()
        mock_get_generator.return_value.generate.assert_called_once_with(
            [chunk1, chunk2]
        )

    def test_propagates_s3_error(self, mock_get_file_from_s3: MagicMock) -> None:
        """An exception raised by get_file_from_s3 must propagate."""
        mock_get_file_from_s3.side_effect = RuntimeError("S3 unavailable")

        with pytest.raises(RuntimeError, match="S3 unavailable"):
            generate_report_from_docx(1, "transcription.docx")


class TestGenerateReportFromDocxSuccess:
    def test_returns_early_when_args_empty(
        self,
        decision_record: DecisionRecord,
        mock_core_api_client: MagicMock,
    ) -> None:
        sender = MagicMock()
        sender.request.args = []

        generate_report_from_docx_success(sender=sender, result=decision_record)

        mock_core_api_client.cls.assert_not_called()

    def test_calls_mark_report_success(
        self,
        decision_record: DecisionRecord,
        mock_core_api_client: MagicMock,
    ) -> None:
        sender = MagicMock()
        sender.request.args = [42]

        generate_report_from_docx_success(sender=sender, result=decision_record)

        mock_core_api_client.mark_report_success.assert_called_once_with(
            meeting_id=42, report=decision_record
        )


class TestSetMeetingFailedStatusOnError:
    def test_calls_mark_report_failure(
        self,
        mock_core_api_client: MagicMock,
    ) -> None:
        set_meeting_failed_status_on_error(
            sender=MagicMock(),
            args=[42, "transcription.docx", "DECISION_RECORD"],
            exception=Exception("LLM timeout"),
        )

        mock_core_api_client.mark_report_failure.assert_called_once_with(meeting_id=42)

    def test_falls_back_to_sender_request_args(
        self,
        mock_core_api_client: MagicMock,
    ) -> None:
        sender = MagicMock()
        sender.request.args = [7]

        set_meeting_failed_status_on_error(sender=sender)

        mock_core_api_client.mark_report_failure.assert_called_once_with(meeting_id=7)

    def test_returns_early_when_no_meeting_id(
        self,
        mock_core_api_client: MagicMock,
    ) -> None:
        sender = MagicMock(spec=[])  # no 'request' attribute

        set_meeting_failed_status_on_error(sender=sender)

        mock_core_api_client.cls.assert_not_called()

    def test_returns_early_when_no_sender_and_no_args(
        self,
        mock_core_api_client: MagicMock,
    ) -> None:
        set_meeting_failed_status_on_error()

        mock_core_api_client.cls.assert_not_called()
