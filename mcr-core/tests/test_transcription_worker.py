from unittest.mock import Mock

import pytest
from celery.exceptions import Ignore
from pytest_mock import MockerFixture

import mcr_meeting.transcription_worker as tw
from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException

MEETING_ID = 123
OWNER = "owner-uuid"


def _patch_start_transcription(mocker: MockerFixture) -> Mock:
    client_cls = mocker.patch.object(tw, "MeetingApiClient")
    client_cls.return_value.start_transcription = mocker.AsyncMock()
    return client_cls.return_value.start_transcription


class TestTaskDelegation:
    def test_diarize_marks_transcription_started_then_delegates(
        self, mocker: MockerFixture
    ) -> None:
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
        run = mocker.patch.object(tw, "run_finalize_transcription", return_value=[])
        client_cls = mocker.patch.object(tw, "MeetingApiClient")
        client_cls.return_value.mark_transcription_as_success = mocker.AsyncMock()

        tw.finalize_transcription(MEETING_ID, OWNER)

        run.assert_called_once_with(MEETING_ID)
        client_cls.return_value.mark_transcription_as_success.assert_called_once_with(
            MEETING_ID, transcription_data=None
        )


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


class TestStateHandling:
    def test_task_body_does_not_self_handle_failure(
        self, mocker: MockerFixture
    ) -> None:
        _patch_start_transcription(mocker)
        mocker.patch.object(tw, "run_diarization", side_effect=RuntimeError("boom"))
        mark_failed = mocker.patch.object(tw, "run_mark_transcription_failed")

        with pytest.raises(RuntimeError):
            tw.diarize(MEETING_ID, OWNER)

        mark_failed.assert_not_called()


class TestFailureErrback:
    def test_errback_marks_meeting_failed(self, mocker: MockerFixture) -> None:
        mark_failed = mocker.patch.object(tw, "run_mark_transcription_failed")

        tw.mark_transcription_failed(MEETING_ID, OWNER)

        mark_failed.assert_called_once_with(MEETING_ID, OWNER)

    def test_errback_never_raises_so_worker_is_not_killed(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            tw, "run_mark_transcription_failed", side_effect=RuntimeError("core down")
        )

        tw.mark_transcription_failed(MEETING_ID, OWNER)


# The base Task centralises Sentry context.
class TestPipelineTaskBase:
    def test_base_task_does_not_override_on_failure(self) -> None:
        assert "on_failure" not in tw.TranscriptionPipelineTask.__dict__
        assert "on_failure" not in tw.MeetingPipelineTask.__dict__

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

    def test_meeting_deleted_is_ignore_so_errback_is_skipped(self) -> None:
        assert issubclass(MeetingDeletedException, Ignore)


def test_no_celery_signal_handlers_remain() -> None:
    assert not hasattr(tw, "handle_transcription_success")
    assert not hasattr(tw, "handle_transcription_fail")
    assert not hasattr(tw, "set_sentry_context_before_transcription")
