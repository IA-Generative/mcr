from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from time import perf_counter

from loguru import logger

from mcr_meeting.app.db import deliverable_repository
from mcr_meeting.app.db.meeting_repository import (
    get_meeting_for_update,
    get_meeting_with_owner,
    update_meeting,
)
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain import deliverable_transitions
from mcr_meeting.app.domain.email import (
    build_transcription_ready_email,
)
from mcr_meeting.app.domain.meeting_transitions import mark_transcription_done
from mcr_meeting.app.domain.transcription_rendering import (
    HasSpeakerTranscription,
    render_transcription_docx,
)
from mcr_meeting.app.infrastructure import email as email_infra
from mcr_meeting.app.infrastructure.s3 import (
    read_full_transcript,
    upload_transcription_to_s3,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.transcription_schema import SpeakerTranscription
from mcr_meeting.app.use_cases._shared.drive_upload import (
    try_upload_deliverable_to_drive,
)
from mcr_meeting.app.use_cases._shared.report_dispatch import (
    dispatch_requested_report,
)

TRANSCRIPTION_FILENAME = "v0.docx"


def complete_transcription(
    meeting_id: int, transcriptions: list[SpeakerTranscription] | None = None
) -> None:
    # This endpoint runs several external I/O stages synchronously before it
    # answers, and can exceed the worker's HTTP timeout (see ticket 1009). Time
    # each stage so we can tell which one is slow when it does — always emitted,
    # not only on error, so the signal survives the worker-side retry.
    timings: dict[str, float] = {}

    meeting = get_meeting_with_owner(meeting_id)

    with _timed("read_transcript", timings):
        segments: Sequence[HasSpeakerTranscription] = (
            transcriptions
            if transcriptions is not None
            else read_full_transcript(meeting_id).segments
        )
    with _timed("render_docx", timings):
        docx_buffer = render_transcription_docx(meeting.name, segments)
    with _timed("s3_upload", timings):
        upload_transcription_to_s3(
            meeting_id=meeting.id,
            filename=TRANSCRIPTION_FILENAME,
            content=docx_buffer,
        )
    with _timed("drive_upload", timings):
        external_url = try_upload_deliverable_to_drive(
            meeting, DeliverableType.TRANSCRIPTION, docx_buffer.getvalue()
        )

    with _timed("db_commit", timings), UnitOfWork():
        # Same lock as request_deliverable: serialises this drain against a
        # concurrent request so a REQUESTED report is never left orphaned.
        locked_meeting = get_meeting_for_update(
            meeting_id, with_deliverables=True, with_owner=True
        )
        mark_transcription_done(locked_meeting)
        locked_meeting.transcription_filename = TRANSCRIPTION_FILENAME
        update_meeting(locked_meeting)
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=locked_meeting.id,
                timestamp=datetime.now(timezone.utc),
                status=MeetingStatus.TRANSCRIPTION_DONE,
            )
        )
        deliverable = deliverable_repository.get_active_by_meeting_and_type(
            meeting_id=locked_meeting.id,
            deliverable_type=DeliverableType.TRANSCRIPTION,
        )
        deliverable_transitions.mark_available(deliverable, external_url)
        _drain_requested_reports(locked_meeting)

    with _timed("notify_email", timings):
        _notify_transcription_ready_best_effort(meeting)

    logger.info(
        "complete_transcription timings meeting={} total={:.2f}s {}",
        meeting_id,
        sum(timings.values()),
        " ".join(f"{stage}={seconds:.2f}s" for stage, seconds in timings.items()),
    )


@contextmanager
def _timed(stage: str, timings: dict[str, float]) -> Iterator[None]:
    start = perf_counter()
    try:
        yield
    finally:
        timings[stage] = perf_counter() - start


def _drain_requested_reports(meeting: Meeting) -> None:
    for report in deliverable_repository.find_requested_reports_by_meeting(meeting.id):
        dispatch_requested_report(meeting, report, report.custom_prompt)


def _notify_transcription_ready_best_effort(meeting: Meeting) -> None:
    try:
        content = build_transcription_ready_email(
            meeting.name or "", meeting_id=meeting.id
        )
        email_infra.send_email(
            to_email=meeting.owner.email,
            subject=content.subject,
            html=content.html,
        )
    except Exception:
        logger.exception("notification failed for meeting {}", meeting.id)
