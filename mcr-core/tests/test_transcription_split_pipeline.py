import json
from io import BytesIO
from unittest.mock import Mock

import pytest
from celery.exceptions import Ignore
from pytest_mock import MockerFixture

import mcr_meeting.app.use_cases.transcription._shared.on_pipeline_failure as opf
import mcr_meeting.transcription_worker as tw
from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException
from mcr_meeting.app.infrastructure import s3
from mcr_meeting.app.infrastructure.unleash import FeatureFlag
from mcr_meeting.app.schemas.celery_types import MCRTranscriptionTasks
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationSegment,
    DiarizedTranscriptionSegment,
    SpeakerTranscription,
)
from mcr_meeting.app.use_cases.transcription._shared.artifacts import (
    DiarizationArtifact,
)
from tests.mocks.in_memory_s3 import InMemoryS3

MEETING_ID = 123
OWNER = "owner-uuid"

PREPROCESSED_KEY = s3.get_preprocessed_audio_object_name(MEETING_ID)
DIARIZATION_KEY = s3.get_diarization_object_name(MEETING_ID)
TRANSCRIPTION_RAW_KEY = s3.get_transcription_raw_object_name(MEETING_ID)

_DIARIZATION = [DiarizationSegment(start=0.0, end=1.0, speaker="A")]
_RAW_SEGMENTS = [
    DiarizedTranscriptionSegment(id=0, start=0.0, end=1.0, text="hello", speaker="A")
]


# Each task reads the right S3 objects and writes its own.
class TestS3HandOff:
    def test_diarize_writes_preprocessed_wav_and_diarization(
        self, in_memory_s3: InMemoryS3, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            tw,
            "run_diarization",
            return_value=DiarizationArtifact(
                preprocessed_audio=BytesIO(b"wav-data"), diarization=_DIARIZATION
            ),
        )

        tw.diarize(MEETING_ID, OWNER)

        assert in_memory_s3.objects[PREPROCESSED_KEY] == b"wav-data"
        assert json.loads(in_memory_s3.objects[DIARIZATION_KEY]) == [
            {"start": 0.0, "end": 1.0, "speaker": "A"}
        ]
        assert TRANSCRIPTION_RAW_KEY not in in_memory_s3.objects

    def test_transcribe_chunks_reads_artifact_and_writes_raw(
        self, in_memory_s3: InMemoryS3, mocker: MockerFixture
    ) -> None:
        s3.write_preprocessed_audio(MEETING_ID, BytesIO(b"wav-data"))
        s3.write_diarization(MEETING_ID, _DIARIZATION)
        run = mocker.patch.object(
            tw, "run_transcribe_chunks", return_value=_RAW_SEGMENTS
        )

        tw.transcribe_chunks(MEETING_ID, OWNER)

        assert json.loads(in_memory_s3.objects[TRANSCRIPTION_RAW_KEY]) == [
            {"id": 0, "start": 0.0, "end": 1.0, "text": "hello", "speaker": "A"}
        ]
        # The pre-processed WAV + diarization are read back from S3 and assembled
        # into the same DiarizationArtifact the in-memory path would have passed.
        artifact = run.call_args.args[0]
        assert artifact.preprocessed_audio.getvalue() == b"wav-data"
        assert artifact.diarization == _DIARIZATION

    def test_finalize_reads_raw_and_marks_success(
        self, in_memory_s3: InMemoryS3, mocker: MockerFixture
    ) -> None:
        s3.write_transcription_raw(MEETING_ID, _RAW_SEGMENTS)
        run = mocker.patch.object(
            tw,
            "run_finalize_transcription",
            return_value=[
                SpeakerTranscription(
                    meeting_id=MEETING_ID,
                    transcription_index=0,
                    speaker="Alice",
                    transcription="hello",
                    start=0.0,
                    end=1.0,
                )
            ],
        )
        client_cls = mocker.patch.object(tw, "MeetingApiClient")
        client_cls.return_value.mark_transcription_as_success = mocker.AsyncMock()

        tw.finalize_transcription(MEETING_ID, OWNER)

        assert run.call_args.args == (MEETING_ID, _RAW_SEGMENTS)
        client_cls.return_value.mark_transcription_as_success.assert_called_once()


# The core benefit: replaying transcribe_chunks never re-diarizes.
class TestRetryPerPhase:
    def test_transcribe_chunks_does_not_rediarize(
        self, in_memory_s3: InMemoryS3, mocker: MockerFixture
    ) -> None:
        s3.write_preprocessed_audio(MEETING_ID, BytesIO(b"wav-data"))
        s3.write_diarization(MEETING_ID, _DIARIZATION)
        mocker.patch.object(tw, "run_transcribe_chunks", return_value=_RAW_SEGMENTS)
        rediarize = mocker.patch.object(tw, "run_diarization")

        tw.transcribe_chunks(MEETING_ID, OWNER)

        rediarize.assert_not_called()


# The transcribe shim routes on STRUCTURAL_SPLIT_ENABLED.
class TestShimRouting:
    def _patch_start_transcription(self, mocker: MockerFixture) -> None:
        client_cls = mocker.patch.object(tw, "MeetingApiClient")
        client_cls.return_value.start_transcription = mocker.AsyncMock()

    def test_flag_off_runs_in_memory_no_chain(
        self, mocker: MockerFixture, create_mock_feature_flag_client: Mock
    ) -> None:
        create_mock_feature_flag_client(
            FeatureFlag.STRUCTURAL_SPLIT_ENABLED, enabled=False
        )
        self._patch_start_transcription(mocker)
        in_memory = mocker.patch.object(tw, "run_transcription_in_task")
        chain_mock = mocker.patch.object(tw, "chain")

        tw.transcribe(MEETING_ID, OWNER)

        in_memory.assert_called_once_with(MEETING_ID, OWNER)
        chain_mock.assert_not_called()

    def test_flag_on_enqueues_chain_no_in_memory(
        self, mocker: MockerFixture, create_mock_feature_flag_client: Mock
    ) -> None:
        create_mock_feature_flag_client(
            FeatureFlag.STRUCTURAL_SPLIT_ENABLED, enabled=True
        )
        self._patch_start_transcription(mocker)
        in_memory = mocker.patch.object(tw, "run_transcription_in_task")
        chain_mock = mocker.patch.object(tw, "chain")

        tw.transcribe(MEETING_ID, OWNER)

        chain_mock.assert_called_once()
        chain_mock.return_value.apply_async.assert_called_once()
        in_memory.assert_not_called()


# Explicit success/failure transitions instead of Celery signals.
class TestStateHandling:
    def test_task_body_does_not_self_handle_failure(
        self, mocker: MockerFixture
    ) -> None:
        # Failure marking is the base Task's on_failure hook, not the body — a
        # bare exception must propagate untouched so Celery records FAILURE and
        # stops the chain.
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


# on_pipeline_failure runs inside the on_failure hook, so it must not let a
# deleted-meeting 404 escape (that would become a Celery internal error).
class TestOnPipelineFailure:
    def test_swallows_meeting_deleted(self, mocker: MockerFixture) -> None:
        client_cls = mocker.patch.object(opf, "MeetingApiClient")
        client_cls.return_value.mark_transcription_as_failed = mocker.AsyncMock(
            side_effect=MeetingDeletedException()
        )

        opf.on_pipeline_failure(MEETING_ID, OWNER, error_code="diarize")

    def test_propagates_unexpected_error(self, mocker: MockerFixture) -> None:
        client_cls = mocker.patch.object(opf, "MeetingApiClient")
        client_cls.return_value.mark_transcription_as_failed = mocker.AsyncMock(
            side_effect=RuntimeError("core unreachable")
        )

        with pytest.raises(RuntimeError):
            opf.on_pipeline_failure(MEETING_ID, OWNER, error_code="diarize")


def test_no_celery_signal_handlers_remain() -> None:
    # Guard: the signal-based state handlers are gone. The success handler in
    # particular would mark a meeting DONE the instant the shim returned, before
    # finalize_transcription runs.
    assert not hasattr(tw, "handle_transcription_success")
    assert not hasattr(tw, "handle_transcription_fail")
    assert not hasattr(tw, "set_sentry_context_before_transcription")
