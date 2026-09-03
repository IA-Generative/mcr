from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.use_cases.fail_stale_captures import fail_stale_captures
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.meeting_transition_record_factory import (
    MeetingTransitionRecordFactory,
)

NOW = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
MAX_AGE = timedelta(hours=18)


def _bot_meeting_in_progress_since(since: datetime) -> Meeting:
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.VISIO,
        start_date=since,
    )
    MeetingTransitionRecordFactory.create(
        meeting_id=meeting.id, status=MeetingStatus.CAPTURE_IN_PROGRESS, timestamp=since
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


def test_a_bot_capture_running_past_the_max_age_is_failed_and_recorded(
    db_session: Session,
) -> None:
    stuck = _bot_meeting_in_progress_since(NOW - MAX_AGE - timedelta(hours=1))

    failed = fail_stale_captures(now=NOW)

    assert [m.id for m in failed] == [stuck.id]
    db_session.refresh(stuck)
    assert stuck.status == MeetingStatus.CAPTURE_FAILED
    assert _status_records(db_session, stuck)[-1] == MeetingStatus.CAPTURE_FAILED


def test_a_bot_capture_still_within_the_max_age_is_left_running(
    db_session: Session,
) -> None:
    live = _bot_meeting_in_progress_since(NOW - timedelta(hours=2))

    failed = fail_stale_captures(now=NOW)

    assert failed == []
    db_session.refresh(live)
    assert live.status == MeetingStatus.CAPTURE_IN_PROGRESS


def test_a_scheduled_meeting_whose_bot_is_connecting_right_now_is_left_alone(
    db_session: Session,
) -> None:
    scheduled_days_ago = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_BOT_IS_CONNECTING,
        name_platform=MeetingPlatforms.COMU,
        creation_date=NOW - timedelta(days=3),
    )
    MeetingTransitionRecordFactory.create(
        meeting_id=scheduled_days_ago.id,
        status=MeetingStatus.CAPTURE_PENDING,
        timestamp=NOW - timedelta(minutes=2),
    )

    failed = fail_stale_captures(now=NOW)

    assert failed == []
    db_session.refresh(scheduled_days_ago)
    assert scheduled_days_ago.status == MeetingStatus.CAPTURE_BOT_IS_CONNECTING


def test_a_bot_stuck_connecting_past_the_max_age_is_marked_connection_failed(
    db_session: Session,
) -> None:
    stuck = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_BOT_IS_CONNECTING,
        name_platform=MeetingPlatforms.COMU,
        creation_date=NOW - timedelta(days=3),
    )
    MeetingTransitionRecordFactory.create(
        meeting_id=stuck.id,
        status=MeetingStatus.CAPTURE_PENDING,
        timestamp=NOW - MAX_AGE - timedelta(hours=1),
    )

    fail_stale_captures(now=NOW)

    db_session.refresh(stuck)
    assert stuck.status == MeetingStatus.CAPTURE_BOT_CONNECTION_FAILED
    assert (
        _status_records(db_session, stuck)[-1]
        == MeetingStatus.CAPTURE_BOT_CONNECTION_FAILED
    )


def test_a_browser_recording_abandoned_past_the_max_age_is_failed(
    db_session: Session,
) -> None:
    since = NOW - MAX_AGE - timedelta(hours=1)
    abandoned = MeetingFactory.create(
        record_meeting=True,
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        creation_date=since,
        start_date=since,
    )
    MeetingTransitionRecordFactory.create(
        meeting_id=abandoned.id,
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        timestamp=since,
    )

    fail_stale_captures(now=NOW)

    db_session.refresh(abandoned)
    assert abandoned.status == MeetingStatus.CAPTURE_FAILED


def test_a_legacy_capture_without_transition_records_falls_back_to_its_creation_date(
    db_session: Session,
) -> None:
    legacy = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.WEBCONF,
        creation_date=NOW - timedelta(days=30),
        start_date=None,
    )

    fail_stale_captures(now=NOW)

    db_session.refresh(legacy)
    assert legacy.status == MeetingStatus.CAPTURE_FAILED
