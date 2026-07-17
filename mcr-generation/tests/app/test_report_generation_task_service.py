"""
Unit tests for report_generation_task_service signal handlers.
"""

import inspect
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pytest import fixture

from mcr_generation.app.schemas.base import (
    CustomMarkdownReport,
    DecisionRecord,
    Header,
    Participant,
    Topic,
)
from mcr_generation.app.schemas.celery_types import extract_report_task_args

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

from mcr_generation.app.exceptions.exceptions import (  # noqa: E402
    ReportCallbackError,
)
from mcr_generation.app.services.report_generation_task_service import (  # noqa: E402
    generate_report_from_docx,
    generate_report_from_docx_success,
    mark_deliverable_in_progress_before_generation,
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


class TestGenerateReportFromDocxSignature:
    """Lock the task signature against the contract used by mcr-core.

    mcr-core dispatches the task with
    ``args=[meeting_id, transcription_object_name, report_type]`` and passes
    ``deliverable_id`` / ``owner_keycloak_uuid`` / ``notes_content`` /
    ``custom_prompt`` via ``kwargs``. Swapping the positional order silently
    binds the wrong values (the original bug #739).
    """

    def test_positional_parameters_order_matches_celery_dispatch(self) -> None:
        signature = inspect.signature(generate_report_from_docx)
        parameter_names = list(signature.parameters)

        assert parameter_names[:3] == [
            "meeting_id",
            "transcription_object_filename",
            "report_type",
        ]

    def test_kwargs_only_parameters_have_defaults(self) -> None:
        signature = inspect.signature(generate_report_from_docx)

        for name in (
            "report_type",
            "deliverable_id",
            "owner_keycloak_uuid",
            "notes_content",
            "custom_prompt",
        ):
            assert signature.parameters[name].default is not inspect.Parameter.empty, (
                f"{name} must have a default so mcr-core can pass it via kwargs"
            )

    def test_accepts_celery_dispatch_shape(
        self,
        decision_record: DecisionRecord,
        mock_load_transcript_chunks: MagicMock,
        mock_create_report_generator: MagicMock,
    ) -> None:
        """Replicates exactly what request_deliverable.py sends via send_task."""
        mock_load_transcript_chunks.return_value = [SimpleNamespace(id=0, text="chunk")]
        mock_create_report_generator.return_value.generate.return_value = (
            decision_record
        )

        args = [42, "transcription.docx", "DECISION_RECORD"]
        kwargs = {
            "owner_keycloak_uuid": "owner-uuid",
            "custom_prompt": "résume",
        }

        generate_report_from_docx(*args, **kwargs)

        mock_load_transcript_chunks.assert_called_once_with("transcription.docx")
        _, factory_kwargs = mock_create_report_generator.call_args
        assert factory_kwargs == {"custom_prompt": "résume"}


class TestGenerateReportFromDocx:
    def test_returns_decision_record_built_from_service_outputs(
        self,
        decision_record: DecisionRecord,
        mock_load_transcript_chunks: MagicMock,
        mock_create_report_generator: MagicMock,
    ) -> None:
        """Happy path: get_generator is mocked and its generate() return value is
        forwarded as-is by the task."""
        chunk1 = SimpleNamespace(id=0, text="chunk1")
        chunk2 = SimpleNamespace(id=1, text="chunk2")
        mock_load_transcript_chunks.return_value = [chunk1, chunk2]
        mock_create_report_generator.return_value.generate.return_value = (
            decision_record
        )

        generate_report_from_docx(1, "transcription.docx", notes_content="raw notes")

        mock_load_transcript_chunks.assert_called_once_with("transcription.docx")
        mock_create_report_generator.assert_called_once()
        mock_create_report_generator.return_value.generate.assert_called_once_with(
            [chunk1, chunk2], notes_content="raw notes"
        )

    def test_propagates_s3_error(self, mock_load_transcript_chunks: MagicMock) -> None:
        """An exception raised while loading the transcript must propagate."""
        mock_load_transcript_chunks.side_effect = RuntimeError("S3 unavailable")

        with pytest.raises(RuntimeError, match="S3 unavailable"):
            generate_report_from_docx(1, "transcription.docx")

    def test_returns_custom_markdown_report_built_from_generator(
        self,
        mock_load_transcript_chunks: MagicMock,
        mock_create_report_generator: MagicMock,
    ) -> None:
        """CUSTOM_REPORT: the generator's CustomMarkdownReport is forwarded as-is."""
        mock_load_transcript_chunks.return_value = [SimpleNamespace(id=0, text="x")]
        custom_report = CustomMarkdownReport(markdown_content="## Risques\n- R1")
        mock_create_report_generator.return_value.generate.return_value = custom_report

        result = generate_report_from_docx(
            1,
            "transcription.docx",
            report_type="CUSTOM_REPORT",
            notes_content="raw notes",
            custom_prompt="Liste les risques",
        )

        assert result is custom_report
        mock_create_report_generator.assert_called_once()
        _, factory_kwargs = mock_create_report_generator.call_args
        assert factory_kwargs == {"custom_prompt": "Liste les risques"}
        mock_create_report_generator.return_value.generate.assert_called_once_with(
            [SimpleNamespace(id=0, text="x")], notes_content="raw notes"
        )


class TestExtractReportTaskArgs:
    def test_returns_deliverable_id_from_kwargs(self) -> None:
        args = extract_report_task_args(
            {
                "args": [42],
                "kwargs": {"owner_keycloak_uuid": "abc", "deliverable_id": 7},
            }
        )

        assert args.meeting_id == 42
        assert args.owner_keycloak_uuid == "abc"
        assert args.deliverable_id == 7

    def test_deliverable_id_absent_raise_value_error(self) -> None:
        with pytest.raises(ValueError):
            extract_report_task_args(
                {"args": [42], "kwargs": {"owner_keycloak_uuid": "abc"}}
            )

    def test_deliverable_id_explicit_none_raise_value_error(self) -> None:
        with pytest.raises(ValueError):
            extract_report_task_args(
                {
                    "args": [42],
                    "kwargs": {"owner_keycloak_uuid": "abc", "deliverable_id": None},
                }
            )


class TestMarkDeliverableInProgressBeforeGeneration:
    @fixture(autouse=True)
    def _no_sleep(self, monkeypatch: MagicMock) -> None:
        monkeypatch.setattr(
            "mcr_generation.app.services.report_generation_task_service.time.sleep",
            lambda _: None,
        )

    def test_calls_in_progress_with_deliverable_id(
        self,
        mock_core_api_client: MagicMock,
    ) -> None:
        mark_deliverable_in_progress_before_generation(
            args=[42],
            kwargs={"owner_keycloak_uuid": "abc", "deliverable_id": 7},
        )

        mock_core_api_client.mark_deliverable_in_progress.assert_called_once_with(
            deliverable_id=7
        )

    def test_callback_failure_does_not_raise(
        self,
        mock_core_api_client: MagicMock,
    ) -> None:
        mock_core_api_client.mark_deliverable_in_progress.side_effect = (
            ReportCallbackError("boom")
        )

        mark_deliverable_in_progress_before_generation(
            args=[42],
            kwargs={"owner_keycloak_uuid": "abc", "deliverable_id": 7},
        )


class TestGenerateReportFromDocxSuccess:
    def test_returns_early_when_args_empty(
        self,
        decision_record: DecisionRecord,
        mock_core_api_client: MagicMock,
    ) -> None:
        sender = MagicMock()
        sender.request.args = []
        sender.request.kwargs = {}

        generate_report_from_docx_success(sender=sender, result=decision_record)

        mock_core_api_client.cls.assert_not_called()

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
