from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.use_cases.fail_stale_transcriptions import (
    fail_stale_transcriptions,
)
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.meeting_transition_record_factory import (
    MeetingTransitionRecordFactory,
)

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
MAX_AGE = timedelta(hours=24)
BROKER_RETRY_WINDOW = timedelta(hours=18)


def _meeting_stuck_in(status: MeetingStatus, since: datetime) -> Meeting:
    meeting = MeetingFactory.create(
        status=status,
        name_platform=MeetingPlatforms.VISIO,
        creation_date=since,
        start_date=since,
    )
    MeetingTransitionRecordFactory.create(
        meeting_id=meeting.id, status=status, timestamp=since
    )
    return meeting


def _status_records(db_session: Session, meeting: Meeting) -> list[MeetingStatus]:
    return [
        record.status
        for record in db_session.query(MeetingTransitionRecord)
        .filter(MeetingTransitionRecord.meeting_id == meeting.id)
        .order_by(MeetingTransitionRecord.timestamp)
        .all()
    ]


def test_a_transcription_running_past_the_max_age_is_failed_and_recorded(
    db_session: Session,
) -> None:
    stuck = _meeting_stuck_in(
        MeetingStatus.TRANSCRIPTION_IN_PROGRESS, NOW - MAX_AGE - timedelta(hours=1)
    )

    failed = fail_stale_transcriptions(now=NOW)

    assert [m.id for m in failed] == [stuck.id]
    db_session.refresh(stuck)
    assert stuck.status == MeetingStatus.TRANSCRIPTION_FAILED
    assert _status_records(db_session, stuck)[-1] == MeetingStatus.TRANSCRIPTION_FAILED


def test_a_transcription_never_picked_up_past_the_max_age_is_failed(
    db_session: Session,
) -> None:
    forgotten = _meeting_stuck_in(
        MeetingStatus.TRANSCRIPTION_PENDING, NOW - MAX_AGE - timedelta(days=90)
    )

    fail_stale_transcriptions(now=NOW)

    db_session.refresh(forgotten)
    assert forgotten.status == MeetingStatus.TRANSCRIPTION_FAILED


def test_a_transcription_started_moments_ago_is_left_running(
    db_session: Session,
) -> None:
    live = _meeting_stuck_in(
        MeetingStatus.TRANSCRIPTION_IN_PROGRESS, NOW - timedelta(hours=1)
    )

    failed = fail_stale_transcriptions(now=NOW)

    assert failed == []
    db_session.refresh(live)
    assert live.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS


def test_a_transcription_still_inside_the_broker_retry_window_is_left_alone(
    db_session: Session,
) -> None:
    redelivered = _meeting_stuck_in(
        MeetingStatus.TRANSCRIPTION_IN_PROGRESS, NOW - BROKER_RETRY_WINDOW
    )

    failed = fail_stale_transcriptions(now=NOW)

    assert failed == []
    db_session.refresh(redelivered)
    assert redelivered.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS


def test_an_imported_meeting_stuck_in_transcription_is_failed_too(
    db_session: Session,
) -> None:
    since = NOW - MAX_AGE - timedelta(hours=1)
    imported = MeetingFactory.create(
        import_meeting=True,
        status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        creation_date=since,
        start_date=since,
    )
    MeetingTransitionRecordFactory.create(
        meeting_id=imported.id,
        status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        timestamp=since,
    )

    fail_stale_transcriptions(now=NOW)

    db_session.refresh(imported)
    assert imported.status == MeetingStatus.TRANSCRIPTION_FAILED


def test_a_legacy_transcription_without_transition_records_falls_back_to_its_creation_date(
    db_session: Session,
) -> None:
    legacy = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_PENDING,
        name_platform=MeetingPlatforms.WEBCONF,
        creation_date=NOW - timedelta(days=400),
        start_date=None,
    )

    fail_stale_transcriptions(now=NOW)

    db_session.refresh(legacy)
    assert legacy.status == MeetingStatus.TRANSCRIPTION_FAILED


def test_a_capture_still_in_progress_is_not_touched_by_the_transcription_sweep(
    db_session: Session,
) -> None:
    capturing = _meeting_stuck_in(
        MeetingStatus.CAPTURE_IN_PROGRESS, NOW - MAX_AGE - timedelta(days=10)
    )

    failed = fail_stale_transcriptions(now=NOW)

    assert failed == []
    db_session.refresh(capturing)
    assert capturing.status == MeetingStatus.CAPTURE_IN_PROGRESS
