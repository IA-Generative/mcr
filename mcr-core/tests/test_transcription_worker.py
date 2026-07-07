from unittest.mock import Mock

import pytest
from celery.exceptions import Ignore
from pytest_mock import MockerFixture

import mcr_meeting.app.infrastructure.speech_to_text_models as stt
import mcr_meeting.transcription_worker as tw
from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException
from mcr_meeting.app.schemas.celery_types import MCRTranscriptionTasks

MEETING_ID = 123
OWNER = "owner-uuid"


def _patch_start_transcription(mocker: MockerFixture) -> Mock:
    client_cls = mocker.patch.object(tw, "MeetingApiClient")
    client_cls.return_value.start_transcription = mocker.AsyncMock()
    return client_cls.return_value.start_transcription


# Les tasks sont de la glue : transitions d'état + délégation au use-case.
# Le hand-off S3 entre phases est testé sur les use-cases
# (tests/use_cases/test_run_*.py).
class TestTaskDelegation:
    def test_diarize_marks_transcription_started_then_delegates(
        self, mocker: MockerFixture
    ) -> None:
        # The status flip to TRANSCRIPTION_IN_PROGRESS happens when a worker
        # picks up the first phase, not at enqueue time — queue-wait estimation
        # depends on it.
        start = _patch_start_transcription(mocker)
        run = mocker.patch.object(tw, "run_diarization")

        tw.diarize(MEETING_ID, OWNER)

        start.assert_called_once_with(MEETING_ID)
        run.assert_called_once()
        assert run.call_args.args[0] == MEETING_ID

    def test_transcribe_chunks_delegates(self, mocker: MockerFixture) -> None:
        run = mocker.patch.object(tw, "run_transcribe_chunks")

        tw.transcribe_chunks(MEETING_ID, OWNER)

        run.assert_called_once()
        assert run.call_args.args[0] == MEETING_ID

    def test_finalize_delegates_and_marks_success_without_payload(
        self, mocker: MockerFixture
    ) -> None:
        # La pipeline split poste le statut seul ; core relit le
        # full_transcript.json que finalize vient d'écrire en S3.
        run = mocker.patch.object(tw, "run_finalize_transcription", return_value=[])
        client_cls = mocker.patch.object(tw, "MeetingApiClient")
        client_cls.return_value.mark_transcription_as_success = mocker.AsyncMock()

        tw.finalize_transcription(MEETING_ID, OWNER)

        run.assert_called_once_with(MEETING_ID)
        client_cls.return_value.mark_transcription_as_success.assert_called_once_with(
            MEETING_ID, transcription_data=None
        )


# The transcribe shim is the legacy monolithic path; the chain is built
# core-side (see tests/use_cases/test_init_transcription.py).
class TestLegacyShim:
    def test_transcribe_marks_started_then_runs_in_memory(
        self, mocker: MockerFixture
    ) -> None:
        start = _patch_start_transcription(mocker)
        in_memory = mocker.patch.object(tw, "run_transcription_in_task")

        tw.transcribe(MEETING_ID, OWNER)

        start.assert_called_once_with(MEETING_ID)
        in_memory.assert_called_once_with(MEETING_ID, OWNER)

    def test_legacy_pipeline_still_posts_the_payload(
        self, mocker: MockerFixture
    ) -> None:
        # Contrat legacy : /transcription/success exige le payload tant que le
        # shim vit — il meurt avec lui.
        mocker.patch.object(tw, "run_diarization")
        mocker.patch.object(tw, "run_transcribe_chunks")
        transcription = Mock()
        transcription.model_dump.return_value = {"speaker": "A"}
        mocker.patch.object(
            tw, "run_finalize_transcription", return_value=[transcription]
        )
        client_cls = mocker.patch.object(tw, "MeetingApiClient")
        client_cls.return_value.mark_transcription_as_success = mocker.AsyncMock()

        tw.run_transcription_in_task(MEETING_ID, OWNER)

        client_cls.return_value.mark_transcription_as_success.assert_called_once_with(
            MEETING_ID, transcription_data=[{"speaker": "A"}]
        )


# Explicit success/failure transitions instead of Celery signals.
class TestStateHandling:
    def test_task_body_does_not_self_handle_failure(
        self, mocker: MockerFixture
    ) -> None:
        # Failure marking is the base Task's on_failure hook, not the body — a
        # bare exception must propagate untouched so Celery records FAILURE and
        # stops the chain.
        _patch_start_transcription(mocker)
        mocker.patch.object(tw, "run_diarization", side_effect=RuntimeError("boom"))
        on_fail = mocker.patch.object(tw, "on_pipeline_failure")

        with pytest.raises(RuntimeError):
            tw.diarize(MEETING_ID, OWNER)

        on_fail.assert_not_called()


# The base Task centralises Sentry context and failure marking.
class TestPipelineTaskBase:
    def test_on_failure_marks_meeting_failed(self, mocker: MockerFixture) -> None:
        on_fail = mocker.patch.object(tw, "on_pipeline_failure")
        task = tw.TranscriptionPipelineTask()
        task.name = MCRTranscriptionTasks.DIARIZE

        task.on_failure(RuntimeError("boom"), "task-id", (MEETING_ID, OWNER), {}, None)

        on_fail.assert_called_once_with(
            MEETING_ID, OWNER, error_code=MCRTranscriptionTasks.DIARIZE
        )

    def test_before_start_sets_sentry_context(self, mocker: MockerFixture) -> None:
        mocker.patch.object(tw, "MeetingApiClient")
        gather = mocker.patch.object(tw, "gather_meeting_context")
        set_ctx = mocker.patch.object(tw, "set_sentry_meeting_context")
        task = tw.TranscriptionPipelineTask()

        task.before_start("task-id", (MEETING_ID, OWNER), {})

        gather.assert_called_once()
        set_ctx.assert_called_once_with(gather.return_value)

    def test_all_pipeline_tasks_use_the_base(self) -> None:
        for task in (
            tw.transcribe,
            tw.diarize,
            tw.transcribe_chunks,
            tw.finalize_transcription,
        ):
            assert isinstance(task, tw.TranscriptionPipelineTask)

    def test_meeting_deleted_is_ignore_so_on_failure_is_skipped(self) -> None:
        # Celery never calls on_failure for Ignore, so a deleted meeting
        # (404 -> MeetingDeletedException) aborts cleanly without being marked
        # FAILED — no special-casing needed in the base Task.
        assert issubclass(MeetingDeletedException, Ignore)


class TestWorkerInit:
    def test_initialize_worker_loads_no_model(self, mocker: MockerFixture) -> None:
        mocker.patch.object(tw, "is_gpu_available", return_value=True)
        mocker.patch.object(tw, "get_gpu_name", return_value="fake-gpu")
        load_whisper = mocker.patch.object(stt, "load_whisper_model")
        load_diarization = mocker.patch.object(stt, "load_diarization_pipeline")

        tw.initialize_worker()

        load_whisper.assert_not_called()
        load_diarization.assert_not_called()


def test_no_celery_signal_handlers_remain() -> None:
    # Guard: the signal-based state handlers are gone. The success handler in
    # particular would mark a meeting DONE the instant the shim returned, before
    # finalize_transcription runs.
    assert not hasattr(tw, "handle_transcription_success")
    assert not hasattr(tw, "handle_transcription_fail")
    assert not hasattr(tw, "set_sentry_context_before_transcription")
